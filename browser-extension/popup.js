document.getElementById('importBtn').addEventListener('click', () => {
  const fileInput = document.getElementById('fileInput');
  if (fileInput.files.length === 0) {
    showStatus('Выберите JSON-файл', 'error');
    return;
  }
  const file = fileInput.files[0];
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const json = JSON.parse(e.target.result);
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
      showStatus('Неверный формат JSON', 'error');
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