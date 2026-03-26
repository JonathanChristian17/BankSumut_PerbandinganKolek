import pandas as pd
df = pd.read_csv('d:\\projectbanksumut\\kolektibilitas app\\tmp_analysis\\kode_kantor_all.csv', sep=None, engine='python')
kc_types = {'CABANG', 'CABANG KOORDINATOR MEDAN', 'CABANG SYARIAH'}
current_kc = None
out = open('d:\\projectbanksumut\\kolektibilitas app\\tmp_analysis\\list_kantor.md', 'w', encoding='utf-8')
out.write("# Daftar Kantor Cabang dan Kantor Cabang Pembantu\n\n")

current_kc = None
for _, row in df.iterrows():
    jenis = str(row['JENIS_KANTOR']).upper().strip()
    nama = str(row['NAMA_KANTOR']).strip()
    kode = str(row['KD_CAB']).strip()
    if 'KANTOR PUSAT' in jenis or 'UNIT USAHA SYARIAH' in nama.upper():
        continue
    if jenis in kc_types:
        current_kc = f"[{kode}] {nama}"
        out.write(f"### KC: {current_kc}\n")
    elif current_kc is not None:
        out.write(f"- KCP: [{kode}] {nama} ({jenis})\n")

out.close()
