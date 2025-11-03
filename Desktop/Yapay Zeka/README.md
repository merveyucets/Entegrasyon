# 🧠 Day 1 – Drone Sensor Data Analysis

Bu çalışma, **Yapay Zeka Yazılım Geliştirme Stajı** hazırlıkları kapsamında veri analizi pratiğidir.  
Amaç: sensör verilerini inceleyip **anomali tespiti (anormal sıcaklık değerleri)** yapmak.

---

## 📊 Kullanılan Teknolojiler
- Python (NumPy, Pandas, Matplotlib)
- Scikit-learn (MinMaxScaler)
- Jupyter Notebook (VS Code içinde)

---

## ⚙️ Adımlar
1. **Veri oluşturma:**  
   - 50 örnekten oluşan `time`, `temperature`, `altitude`, `speed` sütunları oluşturuldu.  
   - `numpy.random.normal()` ile rastgele ama gerçekçi sensör verileri üretildi.

2. **Veri görselleştirme:**  
   - Matplotlib kullanılarak sıcaklık ve yükseklik grafiği çizildi.

3. **Anomali tespiti:**  
   - Ortalama ± 2 standart sapma dışındaki değerler anormal olarak işaretlendi.  
   - Kırmızı noktalar anomaliyi temsil ediyor.

---

