import streamlit as st

# Sayfanın en üstündeki büyük başlık
st.title("Yangın Tespit ve Müdahale Asistanı")

# Sol kenar çubuğunda açılır seçim kutusu; seçilen değer "seviye" değişkenine yazılır
seviye = st.sidebar.selectbox(
    "Alarm seviyesi (test)",               # kutunun üstündeki etiket
    ["NORMAL", "SUPHELI", "DOGRULANMIS"]   # kutudaki seçenekler
)

# Seçilen seviyeye göre farklı renkte kutu göster
if seviye == "NORMAL":
    st.success("NORMAL — Durum sakin")                      # yeşil kutu
elif seviye == "SUPHELI":
    st.warning("ŞÜPHELİ — Operatör onayı bekleniyor")       # sarı kutu
else:
    st.error("DOĞRULANMIŞ YANGIN — Prosedürü başlat")       # kırmızı kutu