# 🤖 AGENT.md: Project Standards & Governance

This document defines the naming conventions, scientific symbols, and bilingual (English/Chinese) translations used throughout the `bsrn` project.

## 📏 Radiometric Parameters

All code variables and documentation must adhere to these standards:

| Acronym | Code Name | Symbol | Full English Name | Full Chinese Name |
| :--- | :--- | :--- | :--- | :--- |
| **GHI** | `ghi` | $G_h$ | global horizontal irradiance | 水平总辐照度 |
| **BNI** | `bni` | $B_n$ | beam normal irradiance | 法向直接辐照度 |
| **DHI** | `dhi` | $D_h$ | diffuse horizontal irradiance | 水平散射辐照度 |
| **LWD** | `lwd` | $L_d$ | downward longwave radiation | 下行长波辐射 |
| **LWU** | `lwu` | $L_u$ | upward longwave radiation | 上行长波辐射 |
| **SZA** | `zenith` | $Z$ | solar zenith angle | 太阳天顶角 |
| **cosSZA** | `mu0` | $\mu_0$ | cosine of SZA | 余弦天顶角 |
| **SAA** | `azimuth` | $\phi$ | solar azimuth angle | 太阳方位角 |
| **GHIC** | `ghi_clear` | $G_{hc}$ | clear-sky GHI | 晴空水平总辐照度 |
| **BNIC** | `bni_clear` | $B_{nc}$ | clear-sky BNI | 晴空法向直接辐照度 |
| **DHIC** | `dhi_clear` | $D_{hc}$ | clear-sky DHI | 晴空水平散射辐照度 |
| **BNIE** | `bni_extra` | $E_{0n}$ | extraterrestrial BNI | 地外法向辐照度 |
| **GHIE** | `ghi_extra` | $E_{0}$ | extraterrestrial GHI | 地外水平辐照度 |
| **SC** | `solar_constant` | $E_{\text{sc}}$ | solar constant | 太阳常数 |
| **CSI** | `kappa` | $\kappa$ | clear-sky index | 晴空指数 |
| **k_t** | `k_t` | $k_t$ | clearness index | 晴朗指数 |
| **k_b** | `k_b` | $k_b$ | beam transmittance | 直射透射率 |
| **k_d** | `k_d` | $k_d$ | diffuse transmittance | 散射透射率 |
| **k** | `k` | $k$ | diffuse fraction | 散射分数 |

---

## 📝 Documentation Rules

### 1. Bilingual Comments (Single-Line)
Format: `Description in English / 对应中文描述`
- Example: `# Fetch data from FTP / 从 FTP 获取数据`

### 2. Docstring Structure (NumPy/SciPy Style)
All functions must include a bilingual description in the summary and parameters.

```python
def function_name(param):
    """
    English summary here.
    此处为中文摘要。

    Parameters
    ----------
    param : type
        English description.
        中文描述。

    Returns
    -------
    result : type
        English description.
        中文描述。
    """
```

### 3. Consistency
- Avoid generic terms like "Direct" or "Global" in isolation. Always use the standardized acronyms or full names defined above.
- LaTeX symbols should be used in READMEs and technical documentation.
- Do not capitalize the long form of abbreviation, e.g., it should be "global horizontal irradiance (GHI)" but not "Global Horizontal Irradiance (GHI)".
- Line length should not exceed 110 characters.
- Title for scientific paper as references should be in sentence case, not title case.
