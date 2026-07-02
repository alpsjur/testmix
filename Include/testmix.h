/*
*******************************************************************************
** Copyright (c) 2002-2021 The ROMS/TOMS Group                               **
**   Licensed under a MIT/X style license                                    **
**   See License_ROMS.txt                                                    **
*******************************************************************************
**
** Options for Test Mix.
**
** Application flag:   TESTMIX
** Input script:       testmix.in
*/


/* BASICS (from norkyst) */
#define SOLVE3D            /* define if solving 3D primitive equations */
#define UV_ADV             /* turn ON advection terms */
#define UV_COR             /* turn ON Coriolis term */
#define DJ_GRADPS          /* Splines density  Jacobian (Shchepetkin, 2000) */
#define NONLIN_EOS         /* define if using nonlinear equation of state */
#define SALINITY           /* define if using salinity */
#define UV_QDRAG           /* turn ON quadratic bottom friction */
#define LIMIT_BSTRESS      /* Limit bottom stress to maintain bottom velocity direction */

/* MIXING (from norkyst) */
#define UV_VIS2            /* turn ON Laplacian horizontal mixing */
#define TS_DIF2            /* turn ON Laplacian horizontal mixing */
#undef TS_MIX_STABILITY    /* weighting diffusion between two time levels */ 

#define MIX_GEO_TS         /* mixing on geopotential (constant Z) surfaces */
#define MIX_S_UV           /* mixing on model surfaces */

#undef RI_SPLINES         /* conservative, parabolic splines reconstruction */
#undef SPLINES_VVISC      /* splines reconstruction of vertical viscosity */
#undef SPLINES_VDIFF      /* splines reconstruction of vertical diffusion */

#define LIMIT_VDIFF         /* do not impose an upper limit on vertical diffusion */
#define LIMIT_VVISC         /* do not impose an upper limit on vertical viscosity */

#define GLS_MIXING
#define N2S2_HORAVG       /* Activate horizontal smoothing of buoyancy/shear */
#define CRAIG_BANNER      /* Craig and Banner wave breaking surface flux */
#define CANUTO_A          /* Canuto A-stability function formulation */
#define CHARNOK           /* Charnok surface roughness from wind stress */
#undef  K_C4ADVECTION


/* OTHER (from romsmix and upwelling) */
#undef  ANA_GRID
#define ANA_INITIAL
#define ANA_SMFLUX
#define ANA_STFLUX
#define ANA_SSFLUX
#define ANA_BTFLUX
#define ANA_BSFLUX

/* Structure drag parametrization */
#define STRUCTURE_DRAG