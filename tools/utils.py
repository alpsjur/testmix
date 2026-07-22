import numpy as np

def compute_z_r(h, hc, theta_s, theta_b, N):
    """
    Compute depths at rho-levels assuming zeta=0 (mean sea level).
    Vtransform=2, Vstretching=5 (Shchepetkin 2010).
    Matches the formula in roms/ROMS/Utility/set_scoord.F lines 512-531.

    Parameters
    ----------
    h          : ndarray (eta_rho, xi_rho), positive downward [m]
    hc, theta_s, theta_b, N : scalar ROMS parameters

    Returns
    -------
    z_r : ndarray (N, eta_rho, xi_rho), negative (sea level = 0)
          Index [0] is the bottom-most rho-level (k=1 in Fortran).
          Index [N-1] is the top-most rho-level (k=N in Fortran).
    """
    k_arr = np.arange(1, N + 1, dtype=float)
    rN    = float(N)

    # Non-uniform s-coordinate (Vstretching=5, matches set_scoord.F line 515-516)
    sc_r = -(k_arr**2 - 2.0*k_arr*rN + k_arr + rN**2 - rN) / (rN**2 - rN) \
           - 0.01*(k_arr**2 - k_arr*rN) / (1.0 - rN)

    # Stretching function: surface part
    if theta_s > 0:
        Csur = (1.0 - np.cosh(theta_s * sc_r)) / (np.cosh(theta_s) - 1.0)
    else:
        Csur = -(sc_r ** 2)

    # Stretching function: bottom enhancement
    if theta_b > 0:
        Cs_r = (np.exp(theta_b * Csur) - 1.0) / (1.0 - np.exp(-theta_b))
    else:
        Cs_r = Csur

    h3d   = h[np.newaxis, :, :]
    sc_3d = sc_r[:, np.newaxis, np.newaxis]
    Cs_3d = Cs_r[:, np.newaxis, np.newaxis]

    # Vtransform=2, zeta=0
    z_r = (hc * sc_3d + h3d * Cs_3d) / (hc + h3d) * h3d
    return z_r   # <= 0


def compute_stretching(h, hc, theta_s, theta_b, N):
    """
    Compute vertical stretching curves (s_rho, Cs_r) and (s_w, Cs_w)
    assuming zeta=0 (mean sea level) for Vtransform=2 and Vstretching=5.

    Parameters
    ----------
    h          : ndarray (eta_rho, xi_rho), positive downward [m]
    hc, theta_s, theta_b, N : scalar ROMS parameters

    Returns
    -------
    s_rho : ndarray (N,), normalized S-coordinates at rho-points
    Cs_r  : ndarray (N,), stretching curves at rho-points
    s_w   : ndarray (N+1,), normalized S-coordinates at w-points
    Cs_w  : ndarray (N+1,), stretching curves at w-points
    """
    # Compute s_rho (N levels) and s_w (N+1 levels)
    k_rho = np.arange(1, N + 1, dtype=float)  # Rho-points
    k_w = np.arange(0, N + 1, dtype=float)    # W-points
    rN = float(N)
    
    # Normalized S-coordinates for rho-points
    s_rho = -(k_rho**2 - 2.0 * k_rho * rN + k_rho + rN**2 - rN) / (rN**2 - rN) \
            - 0.01 * (k_rho**2 - k_rho * rN) / (1.0 - rN)
    # Normalized S-coordinates for w-points
    s_w = -(k_w**2 - 2.0 * k_w * rN + k_w + rN**2 - rN) / (rN**2 - rN) \
          - 0.01 * (k_w**2 - k_w * rN) / (1.0 - rN)

    # Stretching function for rho-points
    if theta_s > 0:
        Csur_rho = (1.0 - np.cosh(theta_s * s_rho)) / (np.cosh(theta_s) - 1.0)
    else:
        Csur_rho = -(s_rho ** 2)

    if theta_b > 0:
        Cs_r = (np.exp(theta_b * Csur_rho) - 1.0) / (1.0 - np.exp(-theta_b))
    else:
        Cs_r = Csur_rho

    # Stretching function for w-points
    if theta_s > 0:
        Csur_w = (1.0 - np.cosh(theta_s * s_w)) / (np.cosh(theta_s) - 1.0)
    else:
        Csur_w = -(s_w ** 2)

    if theta_b > 0:
        Cs_w = (np.exp(theta_b * Csur_w) - 1.0) / (1.0 - np.exp(-theta_b))
    else:
        Cs_w = Csur_w

    return s_rho, Cs_r, s_w, Cs_w