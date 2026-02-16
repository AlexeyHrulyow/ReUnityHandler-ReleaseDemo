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

    const mapping = {
      header_before: 'calendar1',
      header_after: 'calendar2',
      pain_syndrome_before: 'singleLineTextInput1',
      pain_syndrome_after: 'singleLineTextInput2',
      stato_dynamic_before: 'singleLineTextInput3',
      stato_dynamic_after: 'singleLineTextInput4',
      mental_functions_before: 'singleLineTextInput5',
      mental_functions_after: 'singleLineTextInput6',
      internal_organs_before: 'singleLineTextInput7',
      internal_organs_after: 'singleLineTextInput8',
      sensory_functions_before: 'singleLineTextInput9',
      sensory_functions_after: 'singleLineTextInput10',
      vital_activity_before: 'singleLineTextInput11',
      vital_activity_after: 'singleLineTextInput12',
      self_care_before: 'singleLineTextInput13',
      self_care_after: 'singleLineTextInput14',
      mobility_before: 'singleLineTextInput15',
      mobility_after: 'singleLineTextInput16',
      work_ability_before: 'singleLineTextInput17',
      work_ability_after: 'singleLineTextInput18',
      communication_before: 'singleLineTextInput19',
      communication_after: 'singleLineTextInput20',
      total_score_before: 'singleLineTextInput21',
      total_score_after: 'singleLineTextInput22'
    };

    let filled = 0;
    for (const [key, value] of Object.entries(data)) {
      const id = mapping[key];
      if (id) {
        const input = doc.getElementById(id);
        if (input) {
          input.value = value;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          filled++;
        } else {
          console.warn(`Поле ${id} не найдено в iframe`);
        }
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