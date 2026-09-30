Update Proses Bisnis :
1. Dasboard awal komersil dan operasi ganti menjadi bahasa inggris yang lain biarkan, kemudian sebelum muncul form pemohon ada pemberitahuan batasan-batasan PAS visitor departure dan arrival itu sampai area mana saja
2. di http://localhost:8001/pas/pengajuan/buat/ 
	- hilangkan input tujuan/instansi
	- Data Pemohon menjadi PIC penanggung jawab lansung
	- saat memilih Layanan, munculkan nama layanan dan dan Harga layanan dan buat dalam bentuk radio button 
	- nama layanan dan harga : 
	    Lokasi:
        - Departure
        - Arrival

        Jenis Layanan:
        Departure Assistance (maks 5 orang) Rp1.000.000,-
        ⁠Greet Service (Maks. 5 orang) Rp1.000.000,-
        Greet & Desk Service (Maks. 5 orang) Rp1.500.000,-
        Greet Group Service (s.d. 10 orang) Rp2.000.000,-
        Greet & Desk Group service (Meja & Maks. 10 orang) Rp2.500.000
        
	- Dokumen Identitas Pendamping, masukkan nama, NIK dan upload identitas berupa pdf atau semua jenis gambar
	- saat melakukan klik Kirim pengajuan ada proses pengecekan NIK atau nomor identitas apakah masuk daftar black list atau tidak
	- jika ada salah satu NIK yang masuk dalam daftar blacklist maka return untuk memberikan notif bahwa ada NIK yang tidak bisa masuk
	- jika lolos maka arahkan ke pembayaran
	
2. di page komersil ada tempat untuk buat layanan, edit layanan, hapus layanan
	- cek apakah sudah melakukan pembayaran atau tidak dengan memvaliadsi bukti bayar
	- jika valid lanjutkan dengan memberikan validasi untuk di lanjutkan ke operasi

3. di page operasi ada tempat buat, edit, delete NIK, nama pemohon yang masuk daftar blaclist
	- jika ada notif dari komersil cek ulang apakah NIK dan Nama lolos blaclist, jika lolos maka terbitkan PAS untuk di informasikan ke AOCH

4. di page AOCH, ada tempat input data seperti nomor PAS yang di berikan terhadap nama pendamping yang sudah di ajukan, dengan status sudah di terima pemohon, sudah di kembalikan pemohon, dan tanggal, jam penyerahan, maupun pengembalian tercatat, dan ada juga poto orang nya dan ttd elektronik saat menyerahkan, dan cukup di wakilkan oleh PIC pemohon atau yang ditugaskan
	- melakukan verifikasi dan melakukan penyerahan

5. di page komersil, operasi, dan aoch juga ada notifikasi yang menjelaskan visitor yang sudah diberikan, masa berlakunya habis atau sedang berjalan, pas visitor ini berlaku untuk satu hari

6. jika ada pas visitor yang belum di kembalikan dan sudah expired dan untuk mencegah kecurangan bisa dipakai besok pagi, petugas avsec bisa menyuruh pemohon untuk membuka aplikasi, di menu dashboard awal ada menu verifikasi, kemudian masukkan nomor request, atau masukkan nomor pas visitor yang di input oleh AOCH untuk melihat status Aktif atau sudah expired
