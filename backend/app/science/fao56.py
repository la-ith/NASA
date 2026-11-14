"""FAO-56 Penman-Monteith grass reference evapotranspiration, daily time step (FAO-56 chapters 3 and 4).

Each function implements one FAO-56 equation and names it. Inputs and outputs use FAO-56 units:
temperature °C, pressure and vapour pressure kPa, radiation MJ m-2 day-1, wind m s-1, ET mm day-1.
Nothing is rounded inside the calculation; FAO-56's worked examples round intermediate values, which is why
the tests compare with tolerances that match FAO's printed precision.
"""
import math
from dataclasses import dataclass
from datetime import date

SOLAR_CONSTANT = 0.0820  # Gsc, MJ m-2 min-1 (Eq. 21)
STEFAN_BOLTZMANN = 4.903e-9  # σ, MJ K-4 m-2 day-1 (Eq. 39)
GRASS_ALBEDO = 0.23  # α for the hypothetical grass reference crop (Eq. 38)


def atmospheric_pressure(elevation_m: float) -> float:
    """Eq. 7: P = 101.3 ((293 - 0.0065 z) / 293)^5.26 [kPa]."""
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def psychrometric_constant(pressure_kpa: float) -> float:
    """Eq. 8: γ = 0.665e-3 P [kPa °C-1]."""
    return 0.665e-3 * pressure_kpa


def saturation_vapour_pressure(t_c: float) -> float:
    """Eq. 11: e°(T) = 0.6108 exp(17.27 T / (T + 237.3)) [kPa]."""
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def mean_saturation_vapour_pressure(t_max_c: float, t_min_c: float) -> float:
    """Eq. 12: es = (e°(Tmax) + e°(Tmin)) / 2 [kPa]."""
    return (saturation_vapour_pressure(t_max_c) + saturation_vapour_pressure(t_min_c)) / 2.0


def slope_vapour_pressure_curve(t_c: float) -> float:
    """Eq. 13: Δ = 4098 e°(T) / (T + 237.3)^2 [kPa °C-1], with T the mean air temperature."""
    return 4098.0 * saturation_vapour_pressure(t_c) / (t_c + 237.3) ** 2


def actual_vapour_pressure_from_dewpoint(t_dew_c: float) -> float:
    """Eq. 14: ea = e°(Tdew) [kPa]. The preferred FAO-56 route when dewpoint is available."""
    return saturation_vapour_pressure(t_dew_c)


def actual_vapour_pressure_from_rh_extremes(t_max_c: float, t_min_c: float, rh_max: float, rh_min: float) -> float:
    """Eq. 17: ea = (e°(Tmin) RHmax/100 + e°(Tmax) RHmin/100) / 2 [kPa]."""
    return (saturation_vapour_pressure(t_min_c) * rh_max / 100.0
            + saturation_vapour_pressure(t_max_c) * rh_min / 100.0) / 2.0


def actual_vapour_pressure_from_rh_mean(t_max_c: float, t_min_c: float, rh_mean: float) -> float:
    """Eq. 19: ea = RHmean/100 · es [kPa]. FAO-56 calls this the least desirable humidity route."""
    return rh_mean / 100.0 * mean_saturation_vapour_pressure(t_max_c, t_min_c)


def inverse_relative_distance(day_of_year: int) -> float:
    """Eq. 23: dr = 1 + 0.033 cos(2π J / 365)."""
    return 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)


def solar_declination(day_of_year: int) -> float:
    """Eq. 24: δ = 0.409 sin(2π J / 365 - 1.39) [rad]."""
    return 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)


def sunset_hour_angle(latitude_rad: float, declination_rad: float) -> float:
    """Eq. 25: ωs = arccos(-tanφ tanδ) [rad].

    Beyond the polar circles -tanφ tanδ leaves [-1, 1] (polar day or night, possible in northern Alaska).
    The argument is limited to [-1, 1], which gives ωs = π (sun never sets) or 0 (sun never rises).
    """
    return math.acos(max(-1.0, min(1.0, -math.tan(latitude_rad) * math.tan(declination_rad))))


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Eq. 21: Ra = (24·60/π) Gsc dr [ωs sinφ sinδ + cosφ cosδ sin ωs] [MJ m-2 day-1]."""
    phi = math.radians(latitude_deg)
    delta = solar_declination(day_of_year)
    omega_s = sunset_hour_angle(phi, delta)
    return (24.0 * 60.0 / math.pi) * SOLAR_CONSTANT * inverse_relative_distance(day_of_year) * (
        omega_s * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(omega_s))


def daylight_hours(latitude_deg: float, day_of_year: int) -> float:
    """Eq. 34: N = 24 ωs / π [hours]."""
    return 24.0 / math.pi * sunset_hour_angle(math.radians(latitude_deg), solar_declination(day_of_year))


def solar_radiation_from_sunshine(sunshine_hours: float, daylight_h: float, ra: float,
                                  a_s: float = 0.25, b_s: float = 0.50) -> float:
    """Eq. 35 (Angström): Rs = (as + bs n/N) Ra [MJ m-2 day-1]. Used only where measured Rs is absent."""
    return (a_s + b_s * sunshine_hours / daylight_h) * ra


def clear_sky_radiation(ra: float, elevation_m: float) -> float:
    """Eq. 37: Rso = (0.75 + 2e-5 z) Ra [MJ m-2 day-1]."""
    return (0.75 + 2e-5 * elevation_m) * ra


def net_shortwave_radiation(rs: float, albedo: float = GRASS_ALBEDO) -> float:
    """Eq. 38: Rns = (1 - α) Rs [MJ m-2 day-1]."""
    return (1.0 - albedo) * rs


def net_longwave_radiation(t_max_c: float, t_min_c: float, ea_kpa: float, rs: float, rso: float) -> float:
    """Eq. 39: Rnl = σ [(Tmax,K⁴ + Tmin,K⁴)/2] (0.34 - 0.14 √ea) (1.35 Rs/Rso - 0.35) [MJ m-2 day-1].

    FAO-56 limits Rs/Rso to at most 1.0. When Rso is zero (polar night) the cloudiness term cannot be formed,
    so the result is NaN and the caller must treat the day as outside the method's applicability.
    """
    if rso <= 0.0:
        return math.nan
    relative_shortwave = min(rs / rso, 1.0)
    t_max_k, t_min_k = t_max_c + 273.16, t_min_c + 273.16  # FAO-56 uses 273.16 in Eq. 39
    return (STEFAN_BOLTZMANN * (t_max_k ** 4 + t_min_k ** 4) / 2.0
            * (0.34 - 0.14 * math.sqrt(ea_kpa)) * (1.35 * relative_shortwave - 0.35))


def wind_speed_at_2m(wind_speed: float, height_m: float) -> float:
    """Eq. 47: u2 = uz · 4.87 / ln(67.8 z - 5.42) [m s-1]."""
    return wind_speed * 4.87 / math.log(67.8 * height_m - 5.42)


def penman_monteith_et0(t_mean_c: float, net_radiation: float, soil_heat_flux: float, u2: float,
                        es_kpa: float, ea_kpa: float, delta: float, gamma: float) -> float:
    """Eq. 6: ET0 = [0.408 Δ (Rn - G) + γ (900 / (T + 273)) u2 (es - ea)] / [Δ + γ (1 + 0.34 u2)] [mm day-1]."""
    numerator = 0.408 * delta * (net_radiation - soil_heat_flux) + gamma * (900.0 / (t_mean_c + 273.0)) * u2 * (
        es_kpa - ea_kpa)
    return numerator / (delta + gamma * (1.0 + 0.34 * u2))


@dataclass(frozen=True)
class Et0Day:
    """One day's ET0 with every intermediate value, so the evidence screen can show the whole chain."""
    et0_mm: float
    t_mean_c: float
    delta: float
    gamma: float
    es_kpa: float
    ea_kpa: float
    ra: float
    rso: float
    rns: float
    rnl: float
    rn: float
    u2: float


def daily_et0(day: date, latitude_deg: float, t_max_c: float, t_min_c: float, ea_kpa: float, rs: float,
              u2: float, pressure_kpa: float, elevation_m: float) -> Et0Day:
    """Daily FAO-56 Penman-Monteith ET0 from daily weather.

    Tmean follows Eq. 9 (mean of Tmax and Tmin), as FAO-56 prescribes for daily calculations.
    G = 0 for a daily step (Eq. 42). Pressure is the measured or modelled surface pressure; Eq. 7 gives it from
    elevation when no pressure is available. Elevation is still needed for Rso (Eq. 37).
    """
    t_mean = (t_max_c + t_min_c) / 2.0
    delta = slope_vapour_pressure_curve(t_mean)
    gamma = psychrometric_constant(pressure_kpa)
    es = mean_saturation_vapour_pressure(t_max_c, t_min_c)
    doy = day.timetuple().tm_yday
    ra = extraterrestrial_radiation(latitude_deg, doy)
    rso = clear_sky_radiation(ra, elevation_m)
    rns = net_shortwave_radiation(rs)
    rnl = net_longwave_radiation(t_max_c, t_min_c, ea_kpa, rs, rso)
    rn = rns - rnl
    et0 = penman_monteith_et0(t_mean, rn, 0.0, u2, es, ea_kpa, delta, gamma)
    return Et0Day(et0, t_mean, delta, gamma, es, ea_kpa, ra, rso, rns, rnl, rn, u2)
