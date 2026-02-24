console.log('✅ Content script загружен, регистрируем слушатель...');
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('📩 Сообщение получено в content.js:', message);
  if (message.type === 'IMPORT_DATA') {
    handleImport(message.data, sendResponse);
    return true; // асинхронный ответ
  }
});

function handleImport(data, sendResponse) {
  console.log('🔄 handleImport вызван с данными:', data);

  // Функция, которая пытается найти iframe и заполнить
  const attempt = () => {
    const iframe = document.querySelector('iframe[srcdoc]');
    console.log('Поиск iframe, результат:', iframe);
    if (!iframe) {
      // Если iframe ещё нет, повторим через 500 мс
      setTimeout(attempt, 500);
      return;
    }
    // Если нашли, вызываем fill
    fillIframe(iframe, data, sendResponse);
  };

  attempt();
}

function fillIframe(iframe, data, sendResponse) {
  console.log('Заполняем iframe:', iframe);

  const fill = () => {
    const doc = iframe.contentDocument;
    if (!doc) {
      sendResponse({ success: false, error: 'Нет доступа к документу iframe' });
      return;
    }

    let filled = 0;
    // Перебираем все ключи в данных – каждый ключ должен быть id элемента в iframe
    for (const [id, value] of Object.entries(data)) {
      const input = doc.getElementById(id);
      if (input) {
        input.value = value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        filled++;
      } else {
        console.warn(`Поле с id "${id}" не найдено в iframe`);
      }
    }
    sendResponse({ success: true, filled });
  };

  if (iframe.contentDocument?.readyState === 'complete') {
    fill();
  } else {
    iframe.addEventListener('load', fill, { once: true });
  }
}