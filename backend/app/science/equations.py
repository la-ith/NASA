"""Equation register: every numerical output names one of these IDs (spec v4.0, section 5)."""

FAO56 = "Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration. FAO Irrigation and " \
        "Drainage Paper 56. https://www.fao.org/4/x0490e/x0490e00.htm"
TR55 = "USDA Soil Conservation Service (1986). Urban Hydrology for Small Watersheds, Technical Release 55, " \
       "chapter 2 and Table 2-2b"

EQUATIONS = {
    "FAO56-Eq6": ("ET0 = [0.408 Δ (Rn - G) + γ (900 / (T + 273)) u2 (es - ea)] / [Δ + γ (1 + 0.34 u2)]",
                  "mm/day", FAO56),
    "FAO56-Eq7": ("P = 101.3 ((293 - 0.0065 z) / 293)^5.26", "kPa", FAO56),
    "FAO56-Eq8": ("γ = 0.665e-3 P", "kPa/°C", FAO56),
    "FAO56-Eq9": ("Tmean = (Tmax + Tmin) / 2", "°C", FAO56),
    "FAO56-Eq11": ("e°(T) = 0.6108 exp(17.27 T / (T + 237.3))", "kPa", FAO56),
    "FAO56-Eq12": ("es = (e°(Tmax) + e°(Tmin)) / 2", "kPa", FAO56),
    "FAO56-Eq13": ("Δ = 4098 e°(T) / (T + 237.3)^2", "kPa/°C", FAO56),
    "FAO56-Eq14": ("ea = e°(Tdew)", "kPa", FAO56),
    "FAO56-Eq17": ("ea = (e°(Tmin) RHmax/100 + e°(Tmax) RHmin/100) / 2", "kPa", FAO56),
    "FAO56-Eq19": ("ea = RHmean/100 · (e°(Tmax) + e°(Tmin)) / 2", "kPa", FAO56),
    "FAO56-Eq21": ("Ra = (24·60/π) Gsc dr [ωs sinφ sinδ + cosφ cosδ sinωs]", "MJ/m²/day", FAO56),
    "FAO56-Eq23": ("dr = 1 + 0.033 cos(2π J / 365)", "-", FAO56),
    "FAO56-Eq24": ("δ = 0.409 sin(2π J / 365 - 1.39)", "rad", FAO56),
    "FAO56-Eq25": ("ωs = arccos(-tanφ tanδ)", "rad", FAO56),
    "FAO56-Eq34": ("N = 24 ωs / π", "hours", FAO56),
    "FAO56-Eq35": ("Rs = (as + bs n/N) Ra", "MJ/m²/day", FAO56),
    "FAO56-Eq37": ("Rso = (0.75 + 2e-5 z) Ra", "MJ/m²/day", FAO56),
    "FAO56-Eq38": ("Rns = (1 - α) Rs, α = 0.23", "MJ/m²/day", FAO56),
    "FAO56-Eq39": ("Rnl = σ [(Tmax,K⁴ + Tmin,K⁴)/2] (0.34 - 0.14 √ea) (1.35 Rs/Rso - 0.35)", "MJ/m²/day", FAO56),
    "FAO56-Eq40": ("Rn = Rns - Rnl", "MJ/m²/day", FAO56),
    "FAO56-Eq42": ("G ≈ 0 for a daily time step", "MJ/m²/day", FAO56),
    "FAO56-Eq47": ("u2 = uz · 4.87 / ln(67.8 z - 5.42)", "m/s", FAO56),
    "FAO56-Eq58": ("ETc = Kc ET0", "mm/day", FAO56),
    "FAO56-Eq62": ("Kc mid = Kc mid(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3", "-", FAO56),
    "FAO56-Eq63": ("RHmin = 100 e°(Tdew) / e°(Tmax)", "%", FAO56),
    "FAO56-Eq65": ("Kc end = Kc end(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3, if Kc end(Tab) ≥ 0.45",
                   "-", FAO56),
    "FAO56-Eq66": ("Kc,i = Kc,prev + [(i - ΣLprev) / Lstage] (Kc,next - Kc,prev)", "-", FAO56),
    "FAO56-Eq80": ("ETc adj = Ks Kc ET0 (single crop coefficient)", "mm/day", FAO56),
    "FAO56-Eq82": ("TAW = 1000 (θFC - θWP) Zr; layered: TAW = Σ 10 · AWCi · Δzi(cm)", "mm", FAO56),
    "FAO56-Eq83": ("RAW = p TAW", "mm", FAO56),
    "FAO56-Eq84": ("Ks = (TAW - Dr) / ((1 - p) TAW) when Dr > RAW, otherwise Ks = 1", "-", FAO56),
    "FAO56-Eq85": ("Dr,i = Dr,i-1 - (P - RO)i - Ii - CRi + ETc,i + DPi", "mm", FAO56),
    "FAO56-Eq88": ("DPi = (Pi - ROi) + Ii - ETc,i - Dr,i-1 ≥ 0", "mm", FAO56),
    "FAO56-T22-p": ("p = p(Table 22) + 0.04 (5 - ETc), limited to 0.1 ≤ p ≤ 0.8", "-", FAO56),
    "SCS-CN": ("Q = (P - Ia)² / (P - Ia + S) for P > Ia, else 0; S = 25400/CN - 254; Ia = 0.2 S", "mm", TR55),
    "BALANCE": ("Closure: ΣP - ΣRO + ΣI - ΣETa - ΣDP - ΔS = 0, with S = TAW - Dr", "mm",
                "Conservation of mass for the root-zone control volume (spec v4.0, section 5.3)"),
}
