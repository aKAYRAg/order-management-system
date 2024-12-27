# Sipariş Yönetim Sistemi

Bu proje, müşteri siparişlerini dinamik önceliklendirme ile yöneten bir masaüstü uygulamasıdır. Python ve Tkinter kullanılarak geliştirilmiştir.

## Proje Hakkında

Bu proje, bir işletmenin sipariş yönetim sürecini otomatikleştirmek ve optimize etmek için tasarlanmıştır. Sistem, müşteri tipine (Premium/Normal) ve sipariş bekleme süresine göre dinamik bir önceliklendirme algoritması kullanır.

### Önceliklendirme Sistemi

Siparişler aşağıdaki kriterlere göre önceliklendirilir:
- Premium müşteri siparişleri her zaman önceliklidir
- Bekleme süresi arttıkça öncelik puanı artar
- Sipariş miktarı yüksek olan siparişler daha yüksek önceliğe sahiptir

### Gerçek Zamanlı İzleme

Sistem şu özellikleri gerçek zamanlı olarak izler ve günceller:
- Sipariş durumları
- Stok seviyeleri
- Müşteri işlemleri
- Sistem logları

## Özellikler

### Müşteri Yönetimi
- Müşteri bilgilerini görüntüleme
- Müşteri bütçelerini ve harcamalarını takip etme
- Müşteri tiplerini yönetme (Normal/Premium)
- Müşteri listesini otomatik yenileme

### Ürün Yönetimi
- Ürün ekleme/silme
- Stok seviyelerini güncelleme
- Ürün fiyatlarını takip etme
- Ürün listesini filtreleme

### Sipariş İşleme
- Dinamik sipariş önceliklendirme
  - Premium müşteri siparişlerine öncelik
  - Bekleme süresine göre önceliklendirme
  - Sipariş miktarına göre değerlendirme
- Otomatik sipariş kuyruğu yönetimi
- Gerçek zamanlı sipariş durumu güncellemeleri

### Loglama Sistemi
- Detaylı işlem logları
- Gerçek zamanlı log izleme
- Hata ve uyarı takibi
- Log filtreleme ve arama

## Teknik Özellikler

- Çoklu pencere yönetimi
- Otomatik yenileme sistemi
- Veritabanı işlemleri için SQLite kullanımı
- Güvenli oturum yönetimi
- Hata yakalama ve loglama

## Teknik Detaylar

### Veritabanı Yapısı
- SQLite veritabanı kullanılmıştır
- Tablolar:
  - customers (müşteriler)
  - products (ürünler)
  - orders (siparişler)
  - logs (sistem logları)

### Güvenlik Özellikleri
- Şifreler bcrypt ile hashlenir
- SQL injection koruması
- Giriş denemesi sınırlaması
- Oturum yönetimi

### Performans Optimizasyonları
- Veritabanı indeksleme
- Önbellekleme mekanizmaları
- Asenkron veri yenileme
- Bellek yönetimi optimizasyonları

### Hata Yönetimi
- Kapsamlı exception handling
- Detaylı hata logları
- Otomatik kurtarma mekanizmaları
- Kullanıcı dostu hata mesajları

## Gereksinimler

- Python 3.8+
- Tkinter (Python ile birlikte gelir)
- SQLite3 (Python ile birlikte gelir)
- bcrypt==4.0.1
- Pillow==10.0.0

## Kurulum

1. Repository'yi klonlayın:
```bash
git clone https://github.com/aKAYRAg/order-management-system.git
cd order-management-system
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

## Kullanım

1. Uygulamayı başlatın:
```bash
python main.py
```

2. Varsayılan admin hesabı ile giriş yapın:
- Kullanıcı adı: admin
- Şifre: admin123

3. Admin Paneli Özellikleri:
- Müşteri listesini görüntüleme ve yönetme
- Ürün ekleme, silme ve stok güncelleme
- Siparişleri öncelik sırasına göre işleme
- Sistem loglarını izleme

## Proje Yapısı

```
order-management-system/
├── main.py                 # Ana uygulama dosyası
├── auth/
│   └── auth_manager.py     # Kimlik doğrulama yöneticisi
├── database/
│   └── db_manager.py       # Veritabanı yöneticisi
├── gui/
│   ├── admin_panel.py      # Admin panel arayüzü
│   └── login_window.py     # Giriş ekranı
└── requirements.txt        # Bağımlılıklar
```

## Katkıda Bulunma

1. Bu repository'yi fork edin
2. Feature branch'i oluşturun (`git checkout -b feature/YeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/YeniOzellik`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın. 

## Ekran Görüntüleri

### Giriş Ekranı
![Login Screen](screenshots/login.png)
- Güvenli giriş sistemi
- Kullanıcı tipi seçimi
- Şifre sıfırlama seçeneği

### Admin Paneli
![Admin Panel](screenshots/admin_panel.png)
- Çoklu sekme arayüzü
- Gerçek zamanlı veri güncelleme
- Kolay navigasyon

### Sipariş Yönetimi
![Order Management](screenshots/orders.png)
- Öncelikli siparişler listesi
- Sipariş işleme araçları
- Durum göstergeleri


## Örnek Kullanım Senaryoları

### Sipariş İşleme
```python
# Örnek sipariş işleme kodu
order = Order(
    customer_id=1,
    product_id=2,
    quantity=5
)
result = order_manager.process_order(order)
```

### Öncelik Hesaplama
```python
# Öncelik puanı hesaplama
priority_score = calculate_priority(
    customer_type="Premium",
    wait_time=120,  # saniye
    order_quantity=5
)
```

### Log Oluşturma
```python
# Sistem logu oluşturma
log_manager.create_log(
    log_type="INFO",
    message="Sipariş başarıyla işlendi",
    order_id=123
)
``` 
