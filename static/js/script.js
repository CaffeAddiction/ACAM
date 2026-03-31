// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Sekme (Tab) Değiştirme Mantığı
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Aktif sınıfları temizle
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Tıklanan sekmeyi aktif yap
            tab.classList.add('active');
            const targetId = `tab-${tab.dataset.tab}`;
            document.getElementById(targetId).classList.add('active');
        });
    });
});

// Yükleme Animasyonu Kontrolü
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// ---------------------------------------------------------
// KLASİK ŞİFRE KIRMA (TAB 1)
// ---------------------------------------------------------
async function breakCipher() {
    const ciphertext = document.getElementById('ciphertext').value;
    if (!ciphertext) {
        alert("Lütfen şifreli bir metin girin.");
        return;
    }

    showLoading();
    
    // Önceki sonuçları gizle
    document.getElementById('results').classList.add('hidden');
    document.getElementById('aes-ecb-section').classList.add('hidden');
    document.getElementById('decoded-section').classList.add('hidden');

    try {
        const response = await fetch('/api/break', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ciphertext: ciphertext })
        });

        const data = await response.json();
        
        if (data.error) {
            alert("Hata: " + data.error);
            hideLoading();
            return;
        }

        if (data.is_rsa) {
            alert(data.message);
            // Kullanıcıyı otomatik RSA sekmesine yönlendir
            document.querySelector('[data-tab="rsa"]').click();
            document.getElementById('rsa-modulus').value = ciphertext;
            hideLoading();
            return;
        }

        renderClassicalResults(data);

    } catch (error) {
        console.error("API Hatası:", error);
        alert("Sunucuya bağlanılamadı.");
    } finally {
        hideLoading();
    }
}

function renderClassicalResults(data) {
    const resultsPanel = document.getElementById('results');
    resultsPanel.classList.remove('hidden');

    // 1. Format Analizi
    const grid = document.getElementById('analysis-grid');
    grid.innerHTML = `
        <div class="analysis-item">Format: <span>${data.analysis.format}</span></div>
        <div class="analysis-item">Entropi: <span>${data.analysis.entropy}</span></div>
        <div class="analysis-item">Uzunluk: <span>${data.analysis.original_length} char</span></div>
    `;
    
    if (data.decryption && data.decryption.ic !== undefined) {
         grid.innerHTML += `<div class="analysis-item">IC Puanı: <span>${data.decryption.ic}</span></div>`;
    }

    // 2. AES-ECB Zafiyet Uyarısı
    if (data.aes_ecb_warning) {
        const aesSection = document.getElementById('aes-ecb-section');
        const aesDetails = document.getElementById('aes-ecb-details');
        aesSection.classList.remove('hidden');
        aesDetails.innerHTML = `
            <p><strong>Toplam Blok:</strong> ${data.aes_ecb_warning.total_blocks}</p>
            <p><strong>Tekrarlayan Blok:</strong> ${data.aes_ecb_warning.repeated_blocks}</p>
            <p><strong>Tekrar Oranı:</strong> ${(data.aes_ecb_warning.repetition_ratio * 100).toFixed(1)}%</p>
            <p><em>ECB modu güvensizdir: Aynı plaintext blokları aynı ciphertext üretir.</em></p>
        `;
    }

    // 3. Decode Edilmiş Veri (Hex/Base64 vb.)
    const decodedSection = document.getElementById('decoded-section');
    const decodedText = document.getElementById('decoded-text');
    if (data.hex_decoded) {
        decodedSection.classList.remove('hidden');
        decodedText.textContent = data.hex_decoded;
    } else if (data.base64_decoded) {
        decodedSection.classList.remove('hidden');
        decodedText.textContent = data.base64_decoded;
    } else if (data.base32_decoded) {
        decodedSection.classList.remove('hidden');
        decodedText.textContent = data.base32_decoded;
    }

    // 4. Adaylar Listesi
    if (data.decryption && data.decryption.candidates) {
        const candidatesList = document.getElementById('candidates-list');
        candidatesList.innerHTML = '';
        
        data.decryption.candidates.forEach(cand => {
            let keyStr = "";
            if (cand.shift !== undefined && cand.shift !== null) keyStr = `Shift: ${cand.shift}`;
            else if (cand.key && cand.key !== "N/A" && cand.key !== "None") keyStr = `Key: ${cand.key}`;
            
            candidatesList.innerHTML += `
                <div class="candidate-item">
                    <div class="candidate-header">
                        <span class="candidate-algo">${cand.type}</span>
                        <span>Skor: ${cand.score.toFixed(0)}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #a8b2d1;">${keyStr}</div>
                    <div style="margin-top: 5px;">${cand.text}...</div>
                </div>
            `;
        });
    }

    // 5. En İyi Sonuç (Kazanan)
    if (data.decryption && data.decryption.best) {
        const best = data.decryption.best;
        const bestDiv = document.getElementById('best-result');
        
        let keyHtml = "";
        if (best.shift !== undefined && best.shift !== null) {
            keyHtml = `<div class="key-text">🗝️ Kaydırma (Shift): ${best.shift}</div>`;
        } else if (best.key && best.key !== "N/A" && best.key !== "None") {
            keyHtml = `<div class="key-text">🗝️ Gizli Anahtar: ${best.key}</div>`;
        }

        bestDiv.innerHTML = `
            <div style="color: #94a3b8;">Algoritma: <strong style="color: #fff;">${best.type}</strong></div>
            ${keyHtml}
            <div class="success-text">🎉 ÇÖZÜLEN METİN:</div>
            <pre style="margin-top: 10px; border: 1px solid #10b981;">${best.text}</pre>
        `;
    }
}

// ---------------------------------------------------------
// STEGANOGRAFİ (RESİM ANALİZİ) (YENİ TAB)
// ---------------------------------------------------------
async function analyzeStegoImage() {
    const fileInput = document.getElementById('stegoImageInput');
    if (fileInput.files.length === 0) {
        alert("Lütfen analiz edilecek bir resim dosyası seçin (.png veya .bmp).");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    document.getElementById('stegoResult').classList.remove('hidden');
    document.getElementById('stegoRawData').innerText = "Resim taranıyor, pikseller analiz ediliyor...";
    document.getElementById('stegoDecryptedData').innerText = "";

    try {
        const response = await fetch('/api/analyze-stego', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.success) {
            document.getElementById('stegoRawData').innerText = result.hidden_raw;
            // Eğer ACAM şifreyi kırdıysa best candidate'i göster
            if (result.analysis && result.analysis.best) {
                document.getElementById('stegoDecryptedData').innerText = 
                    `[OTONOM KIRICI DEVREDE]\nFormat: ${result.analysis.best.type}\nSonuç: ${result.analysis.best.text}`;
            } else {
                document.getElementById('stegoDecryptedData').innerText = "Metin klasik bir şifreleme formatına uymuyor veya kırılamadı.";
            }
        } else {
            document.getElementById('stegoRawData').innerText = "Hata: " + result.error;
        }
    } catch (error) {
        console.error("Stego error:", error);
        alert("Resim analizi sırasında sunucuya ulaşılamadı.");
    }
}

// ---------------------------------------------------------
// AES-CBC PADDING ORACLE SALDIRISI (YENİ TAB)
// ---------------------------------------------------------
async function runPaddingOracle() {
    const cipherInput = document.getElementById('oracleCiphertext').value.trim();
    const logBox = document.getElementById('oracleProgressLog');
    const resultBox = document.getElementById('oracleDecryptedData');
    
    document.getElementById('oracleResult').classList.remove('hidden');
    resultBox.innerHTML = "";
    logBox.innerHTML = "> ACAM Padding Oracle Motoru Başlatıldı...\n> Hedef sunucuya sahte IV blokları gönderiliyor...\n";
    document.getElementById('oracleLoader').classList.remove('hidden');

    try {
        const response = await fetch('/api/padding-oracle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ciphertext: cipherInput })
        });
        const result = await response.json();

        if (result.success) {
            // Animasyonlu Log Akışı
            let i = 0;
            const steps = result.steps;
            
            function printStep() {
                if (i < steps.length) {
                    logBox.innerHTML += steps[i] + "\n";
                    logBox.scrollTop = logBox.scrollHeight; // Otomatik aşağı kaydır
                    i++;
                    setTimeout(printStep, 20); // Her satır arası 20ms gecikme (Hacker efekti)
                } else {
                    // Loglar bitince asıl sonucu ekrana bas
                    document.getElementById('oracleLoader').classList.add('hidden');
                    logBox.innerHTML += "\n> [SİSTEM] Tüm bloklar başarıyla deşifre edildi.";
                    logBox.scrollTop = logBox.scrollHeight;
                    
                    resultBox.innerHTML = 
                        `<span style="color: #fff; font-weight: bold;">[+] GİZLİ VERİ (PLAIN TEXT):</span>\n\n"${result.decrypted}"\n\n<span style="color: #64748b; font-size: 0.85em;">(Toplam Kırma Süresi: ${result.time} saniye)</span>`;
                }
            }
            printStep(); // Animasyonu başlat

        } else {
            document.getElementById('oracleLoader').classList.add('hidden');
            resultBox.innerHTML = `<span style="color: #ef4444;">Saldırı Başarısız:</span> ${result.error}`;
        }
    } catch (error) {
        document.getElementById('oracleLoader').classList.add('hidden');
        console.error("Oracle error:", error);
        alert("Sunucuya bağlanılamadı.");
    }
}


// ---------------------------------------------------------
// RSA FAKTORİZASYON (TAB)
// ---------------------------------------------------------
async function breakRSA() {
    const modulus = document.getElementById('rsa-modulus').value.trim();
    const e = document.getElementById('rsa-e').value.trim() || 65537;
    const ciphertext = document.getElementById('rsa-ciphertext').value.trim();

    if (!modulus) {
        alert("Lütfen Modulus (n) değerini girin.");
        return;
    }

    showLoading();
    document.getElementById('rsa-results').classList.add('hidden');

    try {
        const response = await fetch('/api/break-rsa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modulus: modulus, e: e, ciphertext: ciphertext })
        });

        const data = await response.json();
        const resDiv = document.getElementById('rsa-result-content');
        document.getElementById('rsa-results').classList.remove('hidden');

        if (data.error) {
            resDiv.innerHTML = `<h3 style="color: var(--error);">Hata</h3><p>${data.error}</p>`;
            return;
        }

        if (data.success) {
            let html = `
                <h3>AI Kararı: ${data.algorithm}</h3>
                <p><strong>Bit Uzunluğu:</strong> ${data.bit_length} bit</p>
                <p><strong>Hesaplama Süresi:</strong> ${data.duration} saniye</p>
                <div class="success-text">🔑 Bulunan Çarpanlar:</div>
                <pre>p = ${data.p}\nq = ${data.q}</pre>
            `;

            if (data.d) {
                html += `
                    <div class="key-text" style="margin-top: 15px;">🗝️ Gizli Anahtar (d) Hesaplandı!</div>
                    <pre style="word-break: break-all;">d = ${data.d}</pre>
                `;
                
                if (data.plaintext_text) {
                     html += `<div class="success-text" style="margin-top:15px;">🎉 ÇÖZÜLEN METİN:</div>
                              <pre style="border: 1px solid #10b981;">${data.plaintext_text}</pre>`;
                } else if (data.plaintext_numeric) {
                     html += `<div class="success-text" style="margin-top:15px;">🔢 ÇÖZÜLEN SAYISAL VERİ:</div>
                              <pre style="border: 1px solid #10b981;">${data.plaintext_numeric}</pre>`;
                }
            } else if (data.decrypt_error) {
                html += `<p style="color: var(--error); margin-top: 10px;">Şifre Çözme Hatası: ${data.decrypt_error}</p>`;
            }

            resDiv.innerHTML = html;
        } else {
            resDiv.innerHTML = `<h3 style="color: var(--warning);">Sonuç Alınamadı</h3><p>${data.message}</p>`;
        }

    } catch (error) {
        console.error(error);
        alert("Sunucuya bağlanılamadı.");
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------
// WIENER'S ATTACK (TAB)
// ---------------------------------------------------------
async function wienerAttack() {
    const n = document.getElementById('wiener-n').value.trim();
    const e = document.getElementById('wiener-e').value.trim();

    if (!n || !e) {
        alert("Lütfen n ve e değerlerini girin.");
        return;
    }

    showLoading();
    document.getElementById('wiener-results').classList.add('hidden');

    try {
        const response = await fetch('/api/wiener', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n: n, e: e })
        });

        const data = await response.json();
        const resDiv = document.getElementById('wiener-result-content');
        document.getElementById('wiener-results').classList.remove('hidden');

        if (data.error) {
            resDiv.innerHTML = `<h3 style="color: var(--error);">Hata</h3><p>${data.error}</p>`;
            return;
        }

        if (data.success) {
            resDiv.innerHTML = `
                <h3>Saldırı Başarılı!</h3>
                <div class="success-text">🔑 Bulunan Çarpanlar:</div>
                <pre>p = ${data.p}\nq = ${data.q}</pre>
                <div class="key-text" style="margin-top: 15px;">🗝️ Gizli Anahtar (d):</div>
                <pre style="border: 1px solid #f59e0b;">d = ${data.d}</pre>
            `;
        } else {
            resDiv.innerHTML = `<h3 style="color: var(--error);">Başarısız</h3><p>Gizli anahtar (d) yeterince küçük değil veya RSA parametreleri geçersiz.</p>`;
        }

    } catch (error) {
        console.error(error);
        alert("Sunucuya bağlanılamadı.");
    } finally {
        hideLoading();
    }
}


async function runHashCrack() {
    const hash = document.getElementById('hashInput').value.trim();
    if (!hash) return;
    showLoading();
    
    try {
        const response = await fetch('/api/hash-crack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hash: hash })
        });
        const result = await response.json();
        
        const resDiv = document.getElementById('hashResult');
        resDiv.classList.remove('hidden');
        
        if (result.success) {
            resDiv.innerHTML = `<span style="color:#10b981;">[+] Tespit: ${result.type}</span><br>
                                <strong>Şifre:</strong> ${result.plaintext}<br>
                                <small>(${result.attempts} deneme | ${result.time}s)</small>`;
        } else {
            resDiv.innerHTML = `<span style="color:#ef4444;">[!] ${result.error}</span>`;
        }
    } catch(e) { alert("Hata"); } finally { hideLoading(); }
}

async function runDesCrack() {
    const cipher = document.getElementById('desInput').value.trim();
    if (!cipher) return;
    showLoading();
    
    try {
        const response = await fetch('/api/des-crack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ciphertext: cipher })
        });
        const result = await response.json();
        
        const resDiv = document.getElementById('desResult');
        resDiv.classList.remove('hidden');
        
        if (result.success) {
            resDiv.innerHTML = `<span style="color:#10b981;">[+] DES Anahtarı Bulundu!</span><br>
                                <strong>Anahtar (Key):</strong> ${result.key} [${result.mode}]<br>
                                <strong>Metin:</strong> ${result.plaintext}<br>
                                <small>(${result.time}s)</small>`;
        } else {
            resDiv.innerHTML = `<span style="color:#ef4444;">[!] ${result.error}</span>`;
        }
    } catch(e) { alert("Hata"); } finally { hideLoading(); }
}


async function runAutoTests() {
    const container = document.getElementById('autoTestResults');
    const loader = document.getElementById('autoTestLoader');
    
    container.classList.add('hidden');
    container.innerHTML = '';
    loader.classList.remove('hidden');

    try {
        const response = await fetch('/api/run-auto-tests');
        const data = await response.json();

        loader.classList.add('hidden');
        container.classList.remove('hidden');

        if (data.success) {
            data.tests.forEach((test, index) => {
                const isSuccess = test.status === "OK";
                const borderColor = isSuccess ? "#10b981" : "#ef4444";
                const bgIcon = isSuccess ? "✅" : "❌";

                const cardHtml = `
                    <div style="background: #1e293b; padding: 15px; border-left: 5px solid ${borderColor}; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px;">
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 12px;">
                            <span style="font-size: 1.1em; color: #f8fafc; font-weight: bold;">
                                [Test ${index + 1}] ${test.name}
                            </span>
                            <span style="color: ${borderColor}; font-weight: bold; font-size: 1.1em; letter-spacing: 1px;">
                                ${bgIcon} ${test.status}
                            </span>
                        </div>
                        
                        <div style="color: #94a3b8; line-height: 1.6; font-size: 0.95em;">
                            <div style="margin-bottom: 12px;">
                                <strong style="color: #cbd5e1; display: block; margin-bottom: 6px;">Hedef (Girdi):</strong> 
                                <div style="background: #0f172a; padding: 10px; border-radius: 4px; border: 1px solid #334155; font-family: 'Courier New', Courier, monospace; word-break: break-all; max-height: 85px; overflow-y: auto; color: #94a3b8;">${test.target}</div>
                            </div>
                            
                            <div style="margin-bottom: 12px;">
                                <strong style="color: #cbd5e1; display: block; margin-bottom: 6px;">Kapsamlı Analiz Raporu:</strong> 
                                <div style="background: #0f172a; padding: 15px; border-radius: 4px; border: 1px solid #334155; font-family: 'Courier New', Courier, monospace; word-break: break-word; max-height: 280px; overflow-y: auto; color: #cbd5e1;">${test.result_html}</div>
                            </div>
                            
                            <div style="margin-top: 10px; font-size: 0.85em; color: #64748b; text-align: right; border-top: 1px dashed #334155; padding-top: 8px;">
                                ⏱️ Çözüm Süresi: ${test.time} saniye
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += cardHtml;
            });
        }
    } catch (error) {
        loader.classList.add('hidden');
        alert("Testler çalıştırılırken sunucu bağlantısı koptu.");
        console.error(error);
    }
}