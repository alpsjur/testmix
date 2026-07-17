# testmix — Design Reference

*Version: July 2026*

---

## 1. Purpose

`testmix` is an idealised single-grid ROMS test case for developing and tuning
the **STRUCTURE_MIXING** parametrisation. The parametrisation adds a frictional
drag term (modelled as drag on an array of cylinders) to the momentum equations
and injects the associated kinetic energy loss directly into the GLS turbulence
closure. The primary tuning target is the dimensionless coefficient **c₄**,
which controls how strongly the extra drag production drives dissipation in the
ψ (length-scale) equation.

The test case is designed to produce a **sustained, near-steady geostrophic
current** that is identical in both a control run (no parametrisation) and a
parametrised run, so that differences in turbulent kinetic energy and mixing
coefficients can be attributed cleanly to c₄.

---

## 2. Governing Equations — STRUCTURE_MIXING

### 2.1 Momentum drag

An additional drag term is added to both horizontal momentum equations:

$$G_d^u = -\tfrac{1}{2} C_D\, a\, u \sqrt{u^2+v^2}, \quad
  G_d^v = -\tfrac{1}{2} C_D\, a\, v \sqrt{u^2+v^2}$$

where $C_D$ is the drag coefficient (`STR_CD` in the input file) and $a$ is
the **structure area density** (m⁻¹), stored in the grid file as the 3-D field
`str_a`.  The field $a$ represents the frontal area of cylinders per unit
volume: $a = N_{\rm cyl} \cdot d / A$, where $N_{\rm cyl}$ is the number of
cylinders, $d$ is the cylinder diameter, and $A$ is the plan-view area over
which the drag is distributed.

The associated loss of mean kinetic energy per unit mass is:

$$P_d = \tfrac{1}{2} C_D\, a \left(u^2+v^2\right)^{3/2}$$

### 2.2 Modified GLS equations

$P_d$ is injected into both the TKE (*k*) and dissipation-rate (*ψ*) equations:

$$\frac{\partial k}{\partial t} + \cdots = \mathcal{D}_k + P + P_d + G - \varepsilon$$

$$\frac{\partial \psi}{\partial t} + \cdots = \mathcal{D}_\psi +
  \frac{\psi}{k}\bigl(c_1 P + c_4 P_d + c_3 G - c_2 \varepsilon\bigr)$$

Standard GLS uses only the shear production $P$ and buoyancy production $G$.
The addition of $P_d$ means that:

- In the *k*-equation, structure drag feeds TKE at the same rate it extracts
  kinetic energy from the mean flow.
- In the *ψ*-equation, the parameter **c₄** weights how strongly this extra
  production drives the turbulent length scale toward smaller values (increased
  dissipation).  A larger c₄ yields a shorter length scale and smaller eddy
  viscosity for the same TKE level.

---

## 3. Domain and Grid

| Parameter | Value | Notes |
|-----------|-------|-------|
| Interior rho-points (Lm × Mm) | 10 × 12 | Total rho-grid: 12 × 14 |
| Grid spacing (DX = DY) | 800 m | Uniform Cartesian |
| Domain size | 8 000 m × 9 600 m | — |
| Depth (H₀) | 150 m | Flat bottom |
| Vertical levels (N) | 40 | — |
| Vertical coordinate | Vtransform=2, Vstretching=5 | Shchepetkin (2010) |
| THETA\_S / THETA\_B / TCLINE | 5.0 / 4.0 / 100 m | Surface-enhanced stretching |
| Coriolis parameter (f₀) | 1.263 × 10⁻⁴ rad/s | Corresponds to ~65 °N |
| Coordinate system | Cartesian | |

The grid file (`testmix_grd.nc`) is created by `scripts/make_idealized_grid.py`.
It includes the 3-D field `str_a` (structure area density, m⁻¹), which is
uniform throughout the water column and set at runtime via the `--str_a`
argument (default 0.01 m⁻¹).

---

## 4. Forcing and Initial Conditions

### 4.1 Geostrophic current

The simulation is **not wind-forced**. Instead, a sustained geostrophic current
is maintained by prescribing a linear SSH slope in the x-direction at all four
open boundaries. The geostrophic balance is:

$$f_0 \, v = g \, \frac{\partial \eta}{\partial x}
\quad \Longrightarrow \quad
\eta(x) = \frac{f_0 \, V_0}{g} \, x$$

For target velocity **V₀ = 0.15 m/s** (northward, i.e. in the y/v-direction):

| Quantity | Value |
|----------|-------|
| SSH slope ∂η/∂x | 1.931 × 10⁻⁶ m/m |
| Total SSH drop across 8 km domain | ≈ 1.5 cm |
| Inertial period | ≈ 13.8 h |

### 4.2 Initial conditions (`Functionals/ana_initial.h`, `#ifdef TESTMIX`)

| Field | Initial value |
|-------|--------------|
| `u`, `ubar` | 0 |
| `v`, `vbar` | 0.15 m/s (depth-uniform) |
| `zeta` | `1.931e-6 × x_rho(i,j)` |
| Temperature | `T0 + 8·exp(z/50)` — surface-intensified warm layer |
| Salinity | S0 = 35 PSU (uniform) |

The temperature profile creates a pycnocline that suppresses vertical mixing in
the interior; surface mixing is then primarily bottom-boundary-layer driven.

### 4.3 Surface fluxes

All surface fluxes are set to zero (analytical, `ANA_SMFLUX`):
- `sustr = svstr = 0` — no wind stress
- Heat and salt fluxes are also zero (`ANA_STFLUX`, `ANA_SSFLUX`, etc.)

This isolates the effect of structure drag on turbulence from any wind-driven
mixing signal.

---

## 5. Boundary Conditions

All four boundaries are **open** (no periodic wrapping). The LBC configuration
is (`W S E N` column order):

| Variable | W | S | E | N | Rationale |
|----------|---|---|---|---|-----------|
| `isFsur` | Cla | Cla | Cla | Cla | Clamped: directly enforces prescribed SSH slope |
| `isUbar` | Fla | Rad | Fla | Rad | Flather on the normal (u) component at W/E |
| `isVbar` | Rad | Fla | Rad | Rad | Flather (inflow) at S; Radiation (outflow) at N |
| `isUvel` | Rad | Rad | Rad | Rad | Free radiation for 3-D fields |
| `isVvel` | Rad | Rad | Rad | Rad | |
| `isMtke` | Rad | Rad | Rad | Rad | |
| `isTvar` | Rad | Rad | Rad | Rad | (both T and S) |

**Design rationale for S/N asymmetry:**
The geostrophic current flows northward (v > 0). The south boundary is the
**inflow** boundary and uses Flather for vbar, prescribing V₀ = 0.15 m/s.
The north boundary is the **outflow** boundary and uses Radiation, letting the
current exit freely without reflection. This prevents the north boundary from
injecting spurious momentum to maintain V₀ when drag has modified the interior
flow.

### Analytical boundary values (`Functionals/ana_fsobc.h`, `ana_m2obc.h`)

**Free surface** (all four boundaries):
```
zeta = ssh_slope × x_rho(i, j)     where ssh_slope = 1.931e-6 m/m
```
At the W/E boundaries j varies along the wall; at S/N boundaries i varies.

**2D momentum** (W, S, E boundaries):
```
ubar = 0          (no cross-boundary flow anywhere)
vbar = 0.15 m/s   (prescribed at W, S, E walls; north uses radiation)
```

---

## 6. Physics Options (`Include/testmix.h`)

### Active CPP flags

| Flag | Purpose |
|------|---------|
| `SOLVE3D` | 3-D primitive equations |
| `UV_ADV` | Momentum advection |
| `UV_COR` | Coriolis |
| `DJ_GRADPS` | Spline density Jacobian (Shchepetkin 2000) |
| `NONLIN_EOS` | Nonlinear equation of state |
| `SALINITY` | Active salinity tracer |
| `UV_QDRAG` | Quadratic bottom friction |
| `LIMIT_BSTRESS` | Limit bottom stress to maintain velocity direction |
| `UV_VIS2` | Laplacian horizontal momentum mixing |
| `TS_DIF2` | Laplacian horizontal tracer diffusion |
| `MIX_GEO_TS` | Tracer mixing on geopotential surfaces |
| `MIX_S_UV` | Momentum mixing on sigma surfaces |
| `GLS_MIXING` | Generic Length-Scale turbulence closure |
| `N2S2_HORAVG` | Horizontal smoothing of N² and S² before GLS |
| `CRAIG_BANNER` | Wave-breaking surface TKE flux |
| `CANUTO_A` | Canuto A stability functions |
| `CHARNOK` | Charnok surface roughness from wind stress |
| `ANA_INITIAL` | Analytical initial conditions |
| `ANA_SMFLUX` | Analytical surface stress (set to zero) |
| `ANA_STFLUX` | Analytical surface heat flux (zero) |
| `ANA_SSFLUX` | Analytical surface salt flux (zero) |
| `ANA_BTFLUX` | Analytical bottom heat flux (zero) |
| `ANA_BSFLUX` | Analytical bottom salt flux (zero) |
| `ANA_FSOBC` | Analytical free-surface OBC |
| `ANA_M2OBC` | Analytical 2-D momentum OBC |
| `STRUCTURE_MIXING` | Structure drag parametrisation |

---

## 7. Turbulence Closure (GLS)

The GLS scheme is configured as **k–ε** (generic exponents p=2, m=1, n=−0.67):

| Parameter | Value | Description |
|-----------|-------|-------------|
| `GLS_P` | 2.0 | |
| `GLS_M` | 1.0 | |
| `GLS_N` | −0.67 | |
| `GLS_CMU0` | 0.5270 | Stability coefficient |
| `GLS_C1` (c₁) | 1.00 | Shear production coefficient |
| `GLS_C2` (c₂) | 1.22 | Dissipation coefficient |
| `GLS_C3M` (c₃⁻) | 0.05 | Buoyancy production (stable) |
| `GLS_C3P` (c₃⁺) | 1.00 | Buoyancy production (unstable) |
| `GLS_SIGK` | 0.80 | Prandtl number for k |
| `GLS_SIGP` | 1.07 | Prandtl number for ψ |
| `GLS_C4` (c₄) | 0.6 (default) | **Structure drag coefficient — tuning target** |
| `GLS_Kmin` | 1 × 10⁻⁸ | Minimum TKE |
| `GLS_Pmin` | 1 × 10⁻⁸ | Minimum ψ |
| `AKK_BAK` | 5 × 10⁻⁶ m²/s | Background diffusivity for k |
| `AKP_BAK` | 5 × 10⁻⁶ m²/s | Background diffusivity for ψ |
| `AKT_BAK` | 1 × 10⁻⁶ m²/s | Background tracer diffusivity |
| `AKV_BAK` | 1 × 10⁻⁵ m²/s | Background momentum diffusivity |

---

## 8. Structure Drag Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `STR_CD` | 0.63 | Drag coefficient $C_D$ |
| `GLS_C4` | 0.6 (default) | ψ-equation structure drag weight |
| `str_a` | 0.01 m⁻¹ (default) | Structure area density (from grid file) |

The `str_a` field is set in `make_idealized_grid.py` and can be varied via
the `--str_a` command-line argument. It is uniform in x, y, and z by default,
with the option to zero it below a specified depth (`--depth_zero`).

---

## 9. Other Physical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `RHO0` | 1025 kg/m³ | Reference density |
| `T0` | 14 °C | Reference temperature |
| `S0` | 35 PSU | Reference salinity |
| `TCOEF` | 1.7 × 10⁻⁴ °C⁻¹ | Thermal expansion coefficient |
| `RDRG2` | 3 × 10⁻³ | Quadratic bottom drag coefficient |
| `Zob` | 0.02 m | Bottom roughness length |
| `GAMMA2` | 1.0 | Free-slip lateral boundary condition |
| `CHARNOK_ALPHA` | 1000 | Charnok roughness coefficient |
| `CRGBAN_CW` | 100 | Craig–Banner wave breaking coefficient |
| `OBCFAC` | 30 | Inflow/outflow nudging ratio at open boundaries |

---

## 10. Time-Stepping

| Parameter | Value | Notes |
|-----------|-------|-------|
| `DT` | 40 s | Baroclinic time step |
| `NDTFAST` | 20 | Barotropic sub-steps per baroclinic step |
| `NTIMES` | 241 920 | Total baroclinic steps = **112 days** |
| History output (`NHIS=90`) | every 1 hour | |
| Averages output (`NAVG=2160`) | every 1 day | |
| Restart output (`NRST=2160`) | every 1 day | |
| Diagnostics (`NDIA=90`) | every 1 hour | |

---

## 11. Tracer Advection Schemes

| Tracer | Horizontal | Vertical |
|--------|-----------|---------|
| Temperature | U3 (3rd-order upstream) | C4 (4th-order centred) |
| Salinity | HSIMT (3rd-order TVD) | HSIMT |

---

## 12. Workflow

### Building
```bash
bash build_roms.sh
```

### Creating the grid
```bash
python scripts/make_idealized_grid.py --str_a 0.01 --output input/testmix_grd.nc
```

### Running the baseline (no parametrisation)
Edit `testmix.h`, set `#undef STRUCTURE_MIXING`, rebuild, then:
```bash
./romsM testmix.in > output/log_control.txt
```

### Sweeping GLS_C4
```bash
bash sweep_gls_c4.sh
```
This script runs several values of `GLS_C4` (e.g. 0.6, 1.0, 1.4) and writes
separate output directories for each.

### Analysis
```bash
python scripts/compare_tke.py     # vertical TKE profiles
python scripts/compare_dtke.py    # TKE difference between runs
python scripts/plot_profiles.py   # full water-column diagnostics
```

---

## 13. Key Physical Scales

| Scale | Value | Formula |
|-------|-------|---------|
| Inertial period | 13.8 h | 2π/f₀ |
| Internal Rossby radius | ~300 km | √(gH)/f₀ (barotropic) |
| Geostrophic velocity | 0.15 m/s | target V₀ |
| SSH slope | 1.931 × 10⁻⁶ m/m | f₀V₀/g |
| Total SSH drop (8 km) | 1.5 cm | slope × Lx |
| Drag production Pₐ (str_a=0.01, V=0.15 m/s) | ~3.2 × 10⁻⁷ m²/s³ | ½ C_D a V³ |

---

## 14. Repository Structure

```
testmix/
├── Include/
│   └── testmix.h               # CPP options
├── Functionals/
│   ├── ana_initial.h           # initial conditions (geostrophic)
│   ├── ana_fsobc.h             # free-surface OBC (SSH slope)
│   ├── ana_m2obc.h             # 2D momentum OBC (V0, ubar=0)
│   ├── ana_smflux.h            # surface stress (zero)
│   ├── ana_ssh.h               # SSH climatology (placeholder)
│   ├── ana_srflux.h            # solar flux (zero / not used)
│   └── ana_grid.h              # (not used; grid read from NetCDF)
├── scripts/
│   ├── make_idealized_grid.py  # creates testmix_grd.nc
│   ├── plot_profiles.py        # vertical profile plots
│   ├── compare_tke.py          # TKE comparison
│   ├── compare_dtke.py         # TKE difference plots
│   └── add_str_a.py            # post-processing helper
├── input/                      # grid and initial files
├── output/                     # simulation output
├── testmix.in                  # main ROMS input file
├── build_roms.sh               # build script
└── sweep_gls_c4.sh             # parameter sweep script
```
