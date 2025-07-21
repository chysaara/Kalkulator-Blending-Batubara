import streamlit as st
import pulp

# --- Konfigurasi Halaman & Judul ---
st.set_page_config(page_title="Optimasi Blending Batubara", layout="wide")
st.title("Aplikasi Kalkulator Blending Batubara")
st.write("Aplikasi ini menggunakan Program Linear (LP) untuk menemukan komposisi blending yang optimal.")

# =======================================================================
# BAGIAN INPUT DATA (SIDEBAR)
# =======================================================================
st.sidebar.header("1. Atur Skenario Blending")

# Pilihan batubara yang akan dicampur
opsi_batubara = st.sidebar.multiselect(
    "Pilih batubara yang akan dicampur:",
    ["ANUGERAH", "LJB", "LJC", "LJE"],
    default=["ANUGERAH", "LJB"]
)

total_kuantitas = st.sidebar.number_input("Total Kuantitas Blend (kg)", value=7.5, min_value=0.1, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.header("2. Atur Komposisi Manual (Opsional)")

# Membuat dictionary untuk menyimpan input manual pengguna
input_manual = {}
sisa_kuantitas = total_kuantitas

# Hanya tampilkan opsi ini jika ada batubara yang dipilih
if opsi_batubara:
    with st.sidebar.expander("Tetapkan Jumlah Komposisi Tertentu"):
        for nama in opsi_batubara:
            # Pengguna bisa memasukkan jumlah dalam kg
            jumlah_manual = st.number_input(f"Jumlah {nama} (kg)", min_value=0.0, max_value=float(sisa_kuantitas), value=0.0, step=0.1, format="%.2f")
            if jumlah_manual > 0:
                input_manual[nama] = jumlah_manual
                sisa_kuantitas -= jumlah_manual # Kurangi sisa kuantitas yang bisa dioptimasi

st.sidebar.markdown("---")
st.sidebar.header("3. Masukkan Spesifikasi Buyer")
min_cv = st.sidebar.number_input("CV Minimum (kcal/kg)", value=5000)
max_cv = st.sidebar.number_input("CV Maksimum (kcal/kg)", value=5050)
max_ash = st.sidebar.number_input("Ash Maksimum (%)", value=8.0, format="%.2f")
max_ts = st.sidebar.number_input("TS Maksimum (%)", value=0.7, format="%.2f")
max_tm = st.sidebar.number_input("TM Maksimum (%)", value=28.0, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.header("4. Masukkan Kualitas Batubara")

data_kualitas = {}
for nama in ["ANUGERAH", "LJB", "LJC", "LJE"]:
    with st.sidebar.expander(f"Kualitas {nama}"):
        data_kualitas[nama] = {
            'cv': st.number_input(f"CV {nama}", value=float(5500 if nama == 'ANUGERAH' else (4900 if nama == 'LJB' else (4350 if nama == 'LJC' else 4000))), format="%.2f"),
            'tm': st.number_input(f"TM {nama} (%)", value=float(17 if nama == 'ANUGERAH' else (26 if nama == 'LJB' else (31 if nama == 'LJC' else 37))), format="%.2f"),
            'ash': st.number_input(f"Ash {nama} (%)", value=float(6 if nama == 'ANUGERAH' else 5), format="%.2f"),
            'ts': st.number_input(f"TS {nama} (%)", value=float(0.4 if nama in ['ANUGERAH', 'LJB'] else (0.3 if nama == 'LJC' else 0.25)), format="%.2f")
        }

# =======================================================================
# BAGIAN LOGIKA OPTIMASI & HASIL
# =======================================================================

if st.sidebar.button("Jalankan Optimasi", type="primary"):
    
    if not opsi_batubara:
        st.error("Silakan pilih minimal satu jenis batubara untuk dicampur.")
    else:
        model = pulp.LpProblem("Optimasi_Blending_Manual", pulp.LpMaximize)
        
        # Variabel hanya dibuat untuk batubara yang TIDAK diinput manual
        x_vars = {nama: pulp.LpVariable(f"Kuantitas_{nama}", lowBound=0, cat='Continuous') for nama in opsi_batubara if nama not in input_manual}
        
        # Gabungkan variabel yang dioptimasi dengan nilai manual
        semua_komponen = {**x_vars, **input_manual}

        # Fungsi Tujuan hanya melibatkan variabel yang dioptimasi
        model += pulp.lpSum([data_kualitas[nama]['cv'] * semua_komponen[nama] for nama in opsi_batubara]), "Total_CV_Blend"
        
        # Total kuantitas yang dioptimasi adalah sisa dari input manual
        model += pulp.lpSum(x_vars.values()) == sisa_kuantitas, "Sisa_Kuantitas"

        # Batasan Kualitas melibatkan SEMUA komponen (manual + optimasi)
        model += pulp.lpSum([data_kualitas[nama]['cv'] * semua_komponen[nama] for nama in opsi_batubara]) >= min_cv * total_kuantitas, "Batas_Bawah_CV"
        model += pulp.lpSum([data_kualitas[nama]['cv'] * semua_komponen[nama] for nama in opsi_batubara]) <= max_cv * total_kuantitas, "Batas_Atas_CV"
        model += pulp.lpSum([data_kualitas[nama]['ash'] * semua_komponen[nama] for nama in opsi_batubara]) <= max_ash * total_kuantitas, "Batas_Ash"
        model += pulp.lpSum([data_kualitas[nama]['ts'] * semua_komponen[nama] for nama in opsi_batubara]) <= max_ts * total_kuantitas, "Batas_TS"
        model += pulp.lpSum([data_kualitas[nama]['tm'] * semua_komponen[nama] for nama in opsi_batubara]) <= max_tm * total_kuantitas, "Batas_TM"

        model.solve()
        
        st.header("Hasil Optimasi")
        status = pulp.LpStatus[model.status]
        
        if status == 'Optimal':
            st.success(f"Status: {status}")
            
            st.subheader("Komposisi Blend Final")
            # Tampilkan hasil gabungan
            for nama in opsi_batubara:
                if nama in input_manual:
                    kuantitas_hasil = input_manual[nama]
                    st.write(f"**{nama}:** `{kuantitas_hasil:.3f}` kg (Input Manual)")
                else:
                    kuantitas_hasil = x_vars[nama].varValue
                    st.write(f"**{nama}:** `{kuantitas_hasil:.3f}` kg (Hasil Optimasi)")

            st.subheader("Prediksi Kualitas Rata-rata")
            # Hitung kualitas berdasarkan hasil gabungan
            hasil_cv = sum([data_kualitas[nama]['cv'] * (x_vars[nama].varValue if nama in x_vars else input_manual[nama]) for nama in opsi_batubara]) / total_kuantitas
            hasil_tm = sum([data_kualitas[nama]['tm'] * (x_vars[nama].varValue if nama in x_vars else input_manual[nama]) for nama in opsi_batubara]) / total_kuantitas
            hasil_ash = sum([data_kualitas[nama]['ash'] * (x_vars[nama].varValue if nama in x_vars else input_manual[nama]) for nama in opsi_batubara]) / total_kuantitas
            hasil_ts = sum([data_kualitas[nama]['ts'] * (x_vars[nama].varValue if nama in x_vars else input_manual[nama]) for nama in opsi_batubara]) / total_kuantitas
            
            st.write(f"**CV:** `{hasil_cv:.2f}` kcal/kg")
            st.write(f"**TM:** `{hasil_tm:.2f}` %")
            st.write(f"**Ash:** `{hasil_ash:.2f}` %")
            st.write(f"**TS:** `{hasil_ts:.2f}` %")
            
        else:
            st.error(f"Status: {status}")
            st.warning("Tidak ditemukan solusi yang memenuhi semua batasan. Coba periksa kembali data input dan spesifikasi Anda.")