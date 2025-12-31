#pragma $pip install pandas
#pragma $pip install pandas-stubs

import pandas as pd

df = pd.DataFrame(
    {
        "World": [
            "Earth",
            "Mars",
        ],
        "Message": ["Earthly Hello", "Marshian Hello"],
    }
)

earth = df[df['World'] == 'Earth']
print(earth['Message'])

mars = df[df['World'] == 'Mars']
print(mars['Message'])
