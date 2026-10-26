"""Read a Dymola result file (MAT v4, 'dsres.mat') without loading the whole trajectory matrix.

Dymola writes Aclass, name, description, dataInfo, data_1 and data_2 as MATLAB v4 matrices. With Aclass row 4 =
'binTrans' the matrices are stored transposed: name is (maxlen x nvar), dataInfo (4 x nvar), data_1 (n1 x 2) and
data_2 (n2 x ntime), each column-major, so one time point of data_2 is contiguous. data_2 is memory-mapped here and
one variable is read as a strided column, which keeps the memory small for the 1e-5 s EMT runs (about a million
stored points). dataInfo[i] = (matrix, signed column): matrix 1 = data_1 (parameters, constant), matrix 2 = data_2,
0 = the abscissa (time); a negative column means the variable is the negated alias of that column.

Cross-checked against scipy.io.loadmat on the SCRX9 result (check_reader() below, run by post.py --selftest).
"""
import numpy as np

_DTYPES = {0: '<f8', 1: '<f4', 2: '<i4', 3: '<i2', 4: '<u2', 5: 'u1'}


def _headers(path):
    out = {}
    with open(path, 'rb') as f:
        while True:
            hdr = f.read(20)
            if len(hdr) < 20:
                break
            mopt, mrows, ncols, imagf, namlen = np.frombuffer(hdr, '<i4')
            name = f.read(int(namlen)).rstrip(b'\0').decode('latin-1')
            p = (int(mopt) // 10) % 10
            dt = np.dtype(_DTYPES[p])
            off = f.tell()
            nbytes = int(mrows) * int(ncols) * dt.itemsize * (2 if imagf else 1)
            out[name] = (int(mrows), int(ncols), dt, off)
            f.seek(off + nbytes)
    return out


class DsRes:
    def __init__(self, path):
        self.path = path
        self.h = _headers(path)
        aclass = self._read_small('Aclass')
        self.trans = (aclass.shape[0] >= 4 and 'binTrans' in aclass[3])
        names = self._read_text('name')
        info = self._read_int('dataInfo')
        self.names = names
        self.info = {n: (int(info[i][0]), int(info[i][1])) for i, n in enumerate(names)}
        r, c, dt, off = self.h['data_1']
        d1 = np.fromfile(path, dtype=dt, count=r * c, offset=off)
        self.data_1 = d1.reshape(c, r).T if self.trans else d1.reshape(r, c, order='F')
        r, c, dt, off = self.h['data_2']
        if self.trans:
            self.data_2 = np.memmap(path, dtype=dt, mode='r', offset=off, shape=(c, r))  # (ntime, nvar)
        else:
            self.data_2 = np.memmap(path, dtype=dt, mode='r', offset=off, shape=(r, c), order='F')
        self.precision = str(dt)

    def _read_raw(self, name):
        r, c, dt, off = self.h[name]
        return r, c, np.fromfile(self.path, dtype=dt, count=r * c, offset=off)

    def _read_small(self, name):
        r, c, a = self._read_raw(name)
        a = a.reshape(c, r).T  # column-major (r x c)
        return np.array([''.join(chr(x) for x in row).rstrip() for row in a])

    def _read_text(self, name):
        r, c, a = self._read_raw(name)
        if self.trans:
            rows = a.reshape(c, r)  # each row one string
        else:
            rows = a.reshape(c, r).T
        return [bytes(row.astype('u1')).split(b'\0')[0].decode('latin-1').rstrip() for row in rows]

    def _read_int(self, name):
        r, c, a = self._read_raw(name)
        return a.reshape(c, r) if self.trans else a.reshape(c, r).T

    @property
    def npoints(self):
        return self.data_2.shape[0] if self.trans else self.data_2.shape[1]

    def time(self):
        return np.array(self.data_2[:, 0] if self.trans else self.data_2[0, :], dtype=float)

    def has(self, name):
        return name in self.info

    def values(self, name):
        mat, col = self.info[name]
        sign = -1.0 if col < 0 else 1.0
        j = abs(col) - 1
        if mat == 0:
            return self.time()
        if mat == 1:
            return np.full(self.npoints, sign * float(self.data_1[j, 0]))
        col_data = self.data_2[:, j] if self.trans else self.data_2[j, :]
        return sign * np.array(col_data, dtype=float)


def check_reader(path, names):
    """Compare this reader with scipy.io.loadmat for a few variables; returns the largest absolute difference."""
    import scipy.io
    m = scipy.io.loadmat(path, chars_as_strings=False)
    rd = DsRes(path)
    nm = [''.join(r).rstrip('\x00 ') for r in np.array(m['name']).T]
    info = m['dataInfo']
    worst = 0.0
    for n in names:
        i = nm.index(n)
        mat, col = int(info[0, i]), int(info[1, i])
        src = m['data_%d' % mat] if mat else m['data_2']
        ref = np.sign(col) * src[abs(col) - 1, :] if mat else src[0, :]
        if mat == 1:
            ref = np.full(rd.npoints, ref[0])
        worst = max(worst, float(np.max(np.abs(rd.values(n) - ref))))
    return worst
