import pandas as pd

df = pd.DataFrame(columns = ['padnumber','xposition','yposition'])


for i in range(12):
    for j in range(3+int(i/2)):
        xpos  = (i%2)*0.54/2 + j*0.54
        ypos = 0.47*(11-i) + 0.47/2
        df.loc[len(df)] = ['',xpos,ypos]

for i2 in range(12):
    i = 11 - i2
    for j2 in range(3+int((i+1)/2)):

        j = 3+int((i+1)/2) - j2 -1
        xpos  = ((i2)%2)*0.54/2 + j2*0.54
        ypos = -0.47*(11-i) -0.47/2
        df.loc[len(df)] = ['',xpos,ypos]

print(df)
df.to_csv(f'./geometries/HR_hex_positions.csv')
