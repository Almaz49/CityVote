with open('names.txt',encoding="UTF-8") as f:
    stroka = f.read()
print(stroka)
spisok = stroka.splitlines()
print(spisok)
for FIO in spisok:
    fam,im,otch = FIO.split(' ')
    print(fam, im)