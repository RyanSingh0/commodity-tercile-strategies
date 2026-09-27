"""Contract metadata: multipliers, the Bloomberg TR sub-index behind each future, names and sectors.

ORDER is my liquidity ranking (average notional volume and open interest). Refined products
(heating oil, RBOB, gasoil) are left out because they move almost one for one with crude.
"""
MULT = {'CL1': 1000, 'CO1': 1000, 'NG1': 10000, 'GC1': 100, 'SI1': 5000, 'HG1': 250, 'PL1': 50, 'PA1': 100,
        'C 1': 50, 'S 1': 50, 'W 1': 50, 'KW1': 50, 'SM1': 100, 'BO1': 600, 'HO1': 420, 'XB1': 420, 'QS1': 100,
        'LA1': 25, 'LL1': 25, 'LX1': 25, 'LN1': 6, 'LT1': 5, 'KC1': 375, 'SB1': 1120, 'CT1': 500, 'CC1': 10,
        'LC1': 400, 'LH1': 400, 'FC1': 500, 'JO1': 150}
TR = {'CL1': 'BCOMCLTR', 'CO1': 'BCOMCOT', 'NG1': 'BCOMNGTR', 'GC1': 'BCOMGCTR', 'SI1': 'BCOMSITR', 'HG1': 'BCOMHGTR',
      'PL1': 'BCOMPLTR', 'C 1': 'BCOMCNTR', 'S 1': 'BCOMSYTR', 'W 1': 'BCOMWHTR', 'KW1': 'BCOMKWT', 'SM1': 'BCOMSMT',
      'BO1': 'BCOMBOTR', 'HO1': 'BCOMHOTR', 'XB1': 'BCOMRBTR', 'QS1': 'BCOMGOT', 'LA1': 'BCOMALTR', 'LL1': 'BCOMPBTR',
      'LX1': 'BCOMZSTR', 'LN1': 'BCOMNITR', 'LT1': 'BCOMSNTR', 'KC1': 'BCOMKCTR', 'SB1': 'BCOMSBTR', 'CT1': 'BCOMCTTR',
      'CC1': 'BCOMCCTR', 'LC1': 'BCOMLCTR', 'LH1': 'BCOMLHTR', 'FC1': 'BCOMFCT', 'PA1': None, 'JO1': None}
NAME = {'CL1': 'WTI Crude Oil', 'CO1': 'Brent Crude Oil', 'NG1': 'Natural Gas', 'GC1': 'Gold', 'SI1': 'Silver',
        'HG1': 'Copper', 'PL1': 'Platinum', 'PA1': 'Palladium', 'C 1': 'Corn', 'S 1': 'Soybeans', 'W 1': 'Wheat (Chicago)',
        'KW1': 'Wheat (Kansas HRW)', 'SM1': 'Soybean Meal', 'BO1': 'Soybean Oil', 'HO1': 'Heating Oil (ULSD)',
        'XB1': 'RBOB Gasoline', 'QS1': 'Low Sulphur Gasoil', 'LA1': 'Aluminium', 'LL1': 'Lead', 'LX1': 'Zinc',
        'LN1': 'Nickel', 'LT1': 'Tin', 'KC1': 'Coffee', 'SB1': 'Sugar', 'CT1': 'Cotton', 'CC1': 'Cocoa',
        'LC1': 'Live Cattle', 'LH1': 'Lean Hogs', 'FC1': 'Feeder Cattle', 'JO1': 'Orange Juice'}
SECTOR = {'CL1': 'Energy', 'CO1': 'Energy', 'NG1': 'Energy', 'HO1': 'Energy', 'XB1': 'Energy', 'QS1': 'Energy',
          'GC1': 'Precious Metals', 'SI1': 'Precious Metals', 'PL1': 'Precious Metals', 'PA1': 'Precious Metals',
          'HG1': 'Industrial Metals', 'LA1': 'Industrial Metals', 'LL1': 'Industrial Metals', 'LX1': 'Industrial Metals',
          'LN1': 'Industrial Metals', 'LT1': 'Industrial Metals', 'C 1': 'Grains', 'S 1': 'Grains', 'W 1': 'Grains',
          'KW1': 'Grains', 'SM1': 'Grains', 'BO1': 'Grains', 'KC1': 'Softs', 'SB1': 'Softs', 'CT1': 'Softs', 'CC1': 'Softs',
          'JO1': 'Softs', 'LC1': 'Livestock', 'LH1': 'Livestock', 'FC1': 'Livestock'}
ORDER = ['CL1', 'CO1', 'GC1', 'NG1', 'S 1', 'SI1', 'LA1', 'C 1', 'HG1']
UNIVERSES = {
    'Top6': (ORDER[:6], [(2, 2, 2)]),
    'Top7': (ORDER[:7], [(3, 2, 2), (2, 3, 2), (2, 2, 3)]),
    'Top8': (ORDER[:8], [(3, 3, 2), (3, 2, 3), (2, 3, 3)]),
    'Top9': (ORDER[:9], [(3, 3, 3)]),
}
SHORT = {'CL1': 'WTI', 'CO1': 'Brent', 'GC1': 'Gold', 'NG1': 'NatGas', 'S 1': 'Soy', 'SI1': 'Silver', 'LA1': 'Alum',
         'C 1': 'Corn', 'HG1': 'Copper'}
