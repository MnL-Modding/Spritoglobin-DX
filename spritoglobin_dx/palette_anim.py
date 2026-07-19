"""Sprite palette animations (the "auxiliary" palette entries).
"""
import struct

TYPE_NAMES = ['?0', 'rotate', 'pingpong', 'crossfade', 'fade', 'add', 'subtract', 'lumatint', 'invert']


def parse(data):
    """Parse an auxiliary entry into {'base', 'table_end', 'slots',
    'slot_offsets'}, or None when there is nothing parseable."""
    if not data or len(data) < 4:
        return None
    count = len(data) // 2
    s = list(struct.unpack(f'<{count}h', data[:count * 2]))
    u = list(struct.unpack(f'<{count}H', data[:count * 2]))
    base = s[0]
    table_end = s[1]

    records = {}
    def record(off):
        if off in records:
            return records[off]
        rec = {
            'type':       s[off],
            'name':       TYPE_NAMES[s[off]] if 0 <= s[off] < len(TYPE_NAMES) else f'?{s[off]}',
            'anim_length': s[off + 1],
            'start_tick':  s[off + 2],
            'duration':    s[off + 3],
            'hold_tick':   s[off + 4],
            'first_color': s[off + 5],
            'color_count': s[off + 6],
        }
        b = off + 7
        t = rec['type']
        if t in (1, 2):
            rec['src'] = s[b]
            rec['src_count'] = s[b + 1]
            steps = rec['src_count'] * 2 if t == 2 else rec['src_count']
            rec['step_durations'] = s[b + 2: b + 2 + steps]
        elif t == 3:
            n = s[b]
            rec['keyframes'] = [{'src': s[b + 1 + i * 3], 'fade': s[b + 2 + i * 3], 'total': s[b + 3 + i * 3]} for i in range(n)]
            rec['final'] = s[b + 1 + n * 3]
        elif 4 <= t <= 8:
            o = b
            rec['src'] = s[o]; o += 1
            if t != 8:
                rec['color'] = u[o]; o += 1
            n = s[o]; o += 1
            rec['keyframes'] = []
            for _ in range(n):
                rec['keyframes'].append({'alpha': s[o], 'fade': s[o + 1], 'total': s[o + 2]})
                o += 3
            rec['final'] = s[o]
        records[off] = rec
        return rec

    lists = {}
    def track_list(off):
        # -1-terminated s16 values, each added to the list's own start
        if off in lists:
            return lists[off]
        result = []
        p = off
        while p < len(s) and s[p] != -1:
            result.append(record(off + s[p]))
            p += 1
        lists[off] = result
        return result

    slots = []
    slot_offsets = []
    for k in range(2, min(table_end, len(s))):
        slot_offsets.append(s[k])
        slots.append(track_list(s[k]) if s[k] else [])
    return {'base': base, 'table_end': table_end, 'slots': slots,
            'slot_offsets': slot_offsets}


def resolve(parsed, target=-1, group=-1):
    """Pick the slot the game's resolver would play, returning its index into
    parsed['slots'] or None. The battle engine only ever calls this with the
    defaults (= fallback slot 2)."""
    if parsed is None or target < -1 or target >= 4:
        return None
    offsets = parsed['slot_offsets']
    def word(k):
        return offsets[k - 2] if 0 <= k - 2 < len(offsets) else 0
    if group < 0:
        k = target + 3
        if k < 2:
            return None
        if parsed['base'] <= k:
            k = 2
        if not word(k):
            k = 2
        return k - 2 if word(k) else None
    k = parsed['base'] + 4 * group + max(target, 0)
    if k < 2 or k >= parsed['table_end']:
        return None
    return k - 2 if word(k) else None


def _keyframe_at(keyframes, final_value, tick, key):
    # move toward the next value over `fade` ticks, then hold until `total`
    for i, kf in enumerate(keyframes):
        nxt = keyframes[i + 1][key] if i + 1 < len(keyframes) else final_value
        if tick < kf['fade']:
            return kf[key], nxt, tick, kf['fade']
        tick -= kf['total']
        if tick < 0 or i == len(keyframes) - 1:
            return kf[key], nxt, 1, 1
    return None


# 5-bit-per-channel RGB555 blends; alpha ranges over 0-32
def _lerp15(a, b, alpha):
    out = 0
    for shift in (0, 5, 10):
        out |= (((((a >> shift) & 31) * (32 - alpha)) >> 5) + ((((b >> shift) & 31) * alpha) >> 5)) << shift
    return out

def _add15(a, b, alpha):
    out = 0
    for shift in (0, 5, 10):
        out |= min(((a >> shift) & 31) + ((((b >> shift) & 31) * alpha) >> 5), 31) << shift
    return out

def _sub15(a, b, alpha):
    out = 0
    for shift in (0, 5, 10):
        out |= max(((a >> shift) & 31) - ((((b >> shift) & 31) * alpha) >> 5), 0) << shift
    return out

def _luma15(a, b, alpha):
    gray = min(((a & 31) + ((a >> 5) & 31) + ((a >> 10) & 31)) >> 1, 31)
    out = 0
    for shift in (0, 5, 10):
        tinted = (((b >> shift) & 31) * gray) >> 5
        out |= (((((a >> shift) & 31) * (32 - alpha)) >> 5) + ((tinted * alpha) >> 5)) << shift
    return out


def _apply_record(palette, rec, tick, colors):
    length = abs(rec['anim_length'])
    if rec['anim_length'] < 0:
        # one-shot: no window, hold the end state
        local = rec['duration'] if tick > length else tick
    else:
        if not length:
            return
        local = (tick % length) - rec['start_tick']
        if local < 0:
            return
        if local >= rec['duration']:
            local = rec['hold_tick']
        elif rec['hold_tick']:
            local %= rec['hold_tick']

    count = min(rec['color_count'], colors - rec['first_color'])
    if count <= 0:
        return
    dst = rec['first_color']
    t = rec['type']

    if t in (1, 2):
        n = rec['src_count']
        snap = palette[rec['src']: rec['src'] + n]
        steps = rec['step_durations']
        j, remaining = 0, local
        while j < len(steps):
            remaining -= steps[j]
            if remaining < 0:
                break
            j += 1
        else:
            j = 0
        if t == 2:  # walk the snapshot back and forth instead of wrapping
            def fold(x, n=n):
                x %= 2 * n
                return x if x < n else 2 * n - 1 - x
        else:
            def fold(x, n=n):
                return x % n
        for i in range(count):
            idx = fold(j + i)
            palette[dst + i] = snap[idx] if idx < len(snap) else 0
    elif t == 3:
        kf = _keyframe_at(rec['keyframes'], rec['final'], local, 'src')
        if kf is None:
            return
        frm, to, num, den = kf
        alpha = (num * 32) // den
        snap = palette[:colors]
        for i in range(count):
            a = snap[frm + i] if frm + i < len(snap) else 0
            b = snap[to + i] if to + i < len(snap) else 0
            palette[dst + i] = _lerp15(a, b, alpha)
    elif 4 <= t <= 8:
        kf = _keyframe_at(rec['keyframes'], rec['final'], local, 'alpha')
        if kf is None:
            return
        frm, to, num, den = kf
        alpha = frm + (num * (to - frm)) // den
        for i in range(count):
            src = palette[rec['src'] + i] if rec['src'] + i < len(palette) else 0
            if t == 4:   palette[dst + i] = _lerp15(src, rec['color'], alpha)
            elif t == 5: palette[dst + i] = _add15(src, rec['color'], alpha)
            elif t == 6: palette[dst + i] = _sub15(src, rec['color'], alpha)
            elif t == 7: palette[dst + i] = _luma15(src, rec['color'], alpha)
            else:        palette[dst + i] = _lerp15(src, (~src) & 0x7fff, alpha)


def apply(palette, records, tick, colors):
    """Return a copy of `palette` (RGB555 u16 list) with a slot's records
    applied at `tick`; `colors` clamps every record's write range."""
    tick = int(tick)
    out = list(palette)
    for rec in records:
        _apply_record(out, rec, tick, colors)
    return out
