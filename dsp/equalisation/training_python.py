import numpy as np
import numba


def partition_signal(signal, partitions, codebook):
    """
    Partition a signal according to their power

    Parameters
    ----------
    signal : array_like
        input signal to partition

    partitions : array_like
        partition vector defining the boundaries between the different blocks

    code   : array_like
        the values to partition tolerance

    Returns
    -------
    quanta : array_like
        partitioned quanta
    """
    quanta = []
    for datum in signal:
        index = 0
        while index < len(partitions) and datum > partitions[index]:
            index += 1
        quanta.append(codebook[index])
    return quanta

@numba.jit(nopython=True)
def partition_value(signal, partitions, codebook):
    """
    Partition a value according to their power

    Parameters
    ----------
    signal : float
        input value to partition

    partitions : array_like
        partition vector defining the boundaries between the different blocks

    code   : array_like
        the values to partition tolerance

    Returns
    -------
    quanta : float
        partitioned quanta
    """
    index = 0
    while index < len(partitions) and signal > partitions[index]:
        index += 1
    quanta = codebook[index]
    return quanta

@numba.jit(nopython=True)
def sum(x):
    y = x.flatten()
    __sum = 0.j
    for i in range(y.size):
        __sum += y[i]
    return __sum

@numba.jit(nopython=True)
def FS_MCMA_adaptive(E, TrSyms, Ntaps, os, mu, wx, R):
    """
    Modified CMA algorithm with adaptive step size to determine the equaliser taps. Details in _[1]. Assumes a normalised signal.

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    R      : complex
       CMA cost constant, the real part applies to the real error the imaginary to the imaginary
    
    Returns
    -------

    err       : array_like
       estimation error for x and y polarisation

    wx    : array_like
       equaliser taps

    Notes
    -----
    ..[1] D. Ashmawy, K. Banovic, E. Abdel-Raheem, M. Youssif, H. Mansour, and M. Mohanna, “Joint MCMA and DD blind equalization algorithm with variable-step size,” Proc. 2009 IEEE Int. Conf. Electro/Information Technol. EIT 2009, no. 1, pp. 174–177, 2009.
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    lm =1
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        err[i] = (np.abs(Xest.real)**2 - R.real) * Xest.real + (np.abs(Xest.imag)**2 - R.imag)*Xest.imag*1.j
        if i > 0:
            if err[i].real*err[i-1].real>0 and err[i].imag*err[i-1].imag>0:
                lm = 0
            else:
                lm = 1
        wx -= mu * err[i] * np.conj(X)
        mu = mu/(1+lm*mu*abs(err[i])**2)
    return err, wx

@numba.jit(nopython=True)
def MCMA_adaptive2(E, TrSyms, Ntaps, os, mu, wx, R, syms, R2):
    err = np.zeros(TrSyms, dtype=np.complex128)
    counter1 = 0
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        err[i] = (np.abs(Xest.real)**2 - R.real) * Xest.real + (np.abs(Xest.imag)**2 - R.imag)*Xest.imag*1.j
        Ri = min(abs(syms-Xest))
        wx -= mu * err[i] * np.conj(X)
        if Ri < R2:
            mu /= 5
            counter1 += 1
    return err, wx, mu, counter1

@numba.jit(nopython=True)
def FS_MCMA(E, TrSyms, Ntaps, os, mu, wx, R):
    """
    Training of the Modified CMA algorithm to determine the equaliser taps. Details in _[1]. Assumes a normalised signal.

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    R      : complex
       CMA cost constant, the real part applies to the real error the imaginary to the imaginary
    
    Returns
    -------

    err       : array_like
       estimation error for x and y polarisation

    wx    : array_like
       equaliser taps

    Notes
    -----
    ..[1] Oh, K. N., & Chin, Y. O. (1995). Modified constant modulus algorithm: blind equalization and carrier phase recovery algorithm. Proceedings IEEE International Conference on Communications ICC ’95, 1, 498–502. http://doi.org/10.1109/ICC.1995.525219
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        #Xest = np.sum(wx * X)
        Xest = sum(wx*X)
        err[i] = (np.abs(Xest.real)**2 - R.real) * Xest.real + (np.abs(Xest.imag)**2 - R.imag)*Xest.imag*1.j
        wx -= mu * err[i] * np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def FS_CMA(E, TrSyms, Ntaps, os, mu, wx, R):
    """
    Training of the CMA algorithm to determine the equaliser taps.

    Parameters
    ----------
    E      : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use for training needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu      : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    R      : float
       CMA cost constant, the real part applies to the real error the imaginary to the imaginary

    Returns
    -------

    err       : array_like
       CMA estimation error for x and y polarisation

    wx        : array_like
       equaliser taps
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(0, TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = np.sum(wx * X)
        err[i] = (abs(Xest)**2 - R)*Xest
        wx -= mu * err[i] *  np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def FS_MRDE(E, TrSyms, Ntaps, os, mu, wx, part, code):
    """
    Training of the Modified RDE algorithm to determine the equaliser taps. Details in _[1]. Assumes a normalised signal.

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use for training the radius directed equaliser, needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    part    : array_like (complex)
       partitioning vector defining the boundaries between the different real and imaginary QAM constellation "rings"

    code    : array_like
       code vector defining the signal powers for the different QAM constellation rings

    Returns
    -------

    err       : array_like
       RDE estimation error for x and y polarisation

    wx    : array_like
       equaliser taps

    Notes
    -----
    ..[1] Oh, K. N., & Chin, Y. O. (1995). Modified constant modulus algorithm: blind equalization and carrier phase recovery algorithm. Proceedings IEEE International Conference on Communications ICC ’95, 1, 498–502. http://doi.org/10.1109/ICC.1995.525219
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        Ssq = Xest.real**2 + 1.j * Xest.imag**2
        R = partition_value(Ssq.real, part.real, code.real) + partition_value(Ssq.imag, part.imag, code.imag)*1.j
        err[i] = (Ssq.real - R.real)*Xest.real + (Ssq.imag - R.imag)*1.j*Xest.imag
        wx -= mu * err[i] * np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def SBD(E, TrSyms, Ntaps, os, mu, wx, symbols):
    """
    Symbol Based Decision (SBD) training function after _[1]. This is a DD error function. This does not implement the neighbor weigthing detailed further in _[1].

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use for training, needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    symbols    : array_like
       the symbols of the QAM format being recovered

    Returns
    -------

    err       : array_like
       CMA estimation error for x and y polarisation

    wx    : array_like
       equaliser taps

    References
    ----------
    ...[1] Filho, M., Silva, M. T. M., & Miranda, M. D. (2008). A FAMILY OF ALGORITHMS FOR BLIND EQUALIZATION OF QAM SIGNALS. In 2011 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) (pp. 6–9).
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        R = symbols[np.argmin(np.abs(Xest-symbols))]
        err[i] = (Xest.real - R.real)*abs(R.real) + (Xest.imag - R.imag)*1.j*abs(R.imag)
        wx -= mu * err[i] * np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def MDDMA(E, TrSyms, Ntaps, os, mu, wx, symbols):
    """
    Modified Decision Directed Modulus Algorithm (MDDMA) after _[1].
    This is a DD error function. 

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use for training, needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    symbols    : array_like
       the symbols of the QAM format being recovered

    Returns
    -------

    err       : array_like
       CMA estimation error for x and y polarisation

    wx    : array_like
       equaliser taps

    References
    ----------
    ...[1] Fernandes, C. A. R., Favier, G., & Mota, J. C. M. (2007). Decision directed adaptive blind equalization based on the constant modulus algorithm. Signal, Image and Video Processing, 1(4), 333–346. http://doi.org/10.1007/s11760-007-0027-2
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = np.sum(wx * X)
        R = symbols[np.argmin(np.abs(Xest-symbols))]
        err[i] = (Xest.real**2 - R.real**2)*Xest.real + (Xest.imag**2 - R.imag**2)*1.j*Xest.imag
        wx -= mu * err[i] * np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def FS_RDE(E, TrSyms, Ntaps, os, mu, wx, part, code):
    """
    Training of the RDE algorithm to determine the equaliser taps.

    Parameters
    ----------
    E       : array_like
       dual polarisation signal field

    TrSyms : int
       number of symbols to use for training the radius directed equaliser, needs to be less than len(Ex)

    Ntaps   : int
       number of equaliser taps

    os      : int
       oversampling factor

    mu   : float
       step size parameter

    wx     : array_like
       initial equaliser taps

    part    : array_like
       partitioning vector defining the boundaries between the different QAM constellation rings

    code    : array_like
       code vector defining the signal powers for the different QAM constellation rings

    Returns
    -------

    err       : array_like
       CMA estimation error for x and y polarisation

    wx    : array_like
       equaliser taps
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        Ssq = abs(Xest)**2
        S_DD = partition_value(Ssq, part, code)
        err[i] = (Ssq - S_DD)*Xest
        wx -= mu * err[i] * np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def FS_CME(E, TrSyms, Ntaps, os, mu, wx, R, d, beta):
    """Constellation matched error algorithm after _[1]

    References
    ----------
    ...[1] He, L., Amin, M. G., Reed, C., & Malkemes, R. C. (2004). A Hybrid Adaptive Blind Equalization Algorithm for QAM Signals in Wireless Communications, 52(7), 2058–2069.
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms-33):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        err[i] = (abs(Xest)**2 - R)*Xest
        err[i] +=  beta * np.pi/(2*d) * (np.sin(Xest.real*np.pi/d) + 1.j * np.sin(Xest.imag*np.pi/d)) 
        wx -= mu * err[i] *  np.conj(X)
    return err, wx

@numba.jit(nopython=True)
def FS_SCA(E, TrSyms, Ntaps, os, mu, wx, R):
    """Constellation matched error algorithm after _[1]

    References
    ----------
    ...[1] Sheikh, S. A., & Fan, P. (2008). New blind equalization techniques based on improved square contour algorithm ✩, 18, 680–693. http://doi.org/10.1016/j.dsp.2007.09.001
    """
    err = np.zeros(TrSyms, dtype=np.complex128)
    for i in range(TrSyms-33):
        X = E[:, i * os:i * os + Ntaps]
        Xest = sum(wx * X)
        if abs(Xest.real) >= abs(Xest.imag):
            A = 1
            if abs(Xest.real) == abs(Xest.imag):
                B = 1
            else:
                B = 0
        else:
            A = 0
            B = 1
        err[i] = 4*Xest.real*(4*Xest.real**2 - 4*R**2)*A + 1.j*4*Xest.imag*(4*Xest.imag**2 - 4*R**2)*B
        wx -= mu * err[i] *  np.conj(X)
    return err, wx

