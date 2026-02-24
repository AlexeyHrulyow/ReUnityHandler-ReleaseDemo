document.getElementById('importBtn').addEventListener('click', () => {
  const fileInput = document.getElementById('fileInput');
  if (fileInput.files.length === 0) {
    showStatus('Выберите JSON-файл', 'error');
    return;
  }
  const file = fileInput.files[0];
  const reader = new FileReader();
  reader.onload = (e) => {
    let rawText = e.target.result;
    console.log('Raw content (first 200 chars):', rawText.substring(0, 200));

    // Удаляем BOM (Byte Order Mark), если он есть
    if (rawText.charCodeAt(0) === 0xFEFF) {
      rawText = rawText.substring(1);
    }

    try {
      const json = JSON.parse(rawText);
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        console.log('Активная вкладка:', tabs[0].url);
        chrome.tabs.sendMessage(tabs[0].id, { type: 'IMPORT_DATA', data: json }, (response) => {
          if (chrome.runtime.lastError) {
            console.error('Ошибка отправки:', chrome.runtime.lastError);
            showStatus('Ошибка: ' + chrome.runtime.lastError.message, 'error');
          } else if (response && response.success) {
            showStatus('✓ Данные импортированы', 'success');
          } else {
            showStatus('✗ Ошибка: ' + (response?.error || 'Неизвестная ошибка'), 'error');
          }
        });
      });
    } catch (err) {
      console.error('Ошибка парсинга JSON:', err);
      showStatus('Неверный формат JSON: ' + err.message, 'error');
    }
  };
  reader.readAsText(file);
});

function showStatus(msg, type) {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = msg;
  statusDiv.className = type;
  console.log('Статус:', msg, type);
}