import "toastui-editor-all";
import "uk-ua";

// The library is local. Neither usage tracking nor automatic remote assets are enabled.
export default {
  template: `
    <section :class="{'show-preview': preview}" aria-label="Редактор Markdown">
      <div class="markdown-tools" role="toolbar" aria-label="Форматування Markdown">
        <button v-for="tool in tools" :key="tool.command" type="button"
          class="btn ghost" :title="tool.hint" :aria-label="tool.label"
          @mousedown.prevent @click="format(tool)">{{ tool.label }}</button>
        <button type="button" class="btn ghost" :aria-pressed="preview"
          title="Показати або приховати оформлений текст" @click="preview = !preview">
          <span class="ico ico-doc" aria-hidden="true"></span>Перегляд
        </button>
      </div>
      <details class="markdown-help">
        <summary>Підказки Markdown</summary>
        <p>Виділіть текст і натисніть кнопку форматування. Ctrl+B — жирний,
          Ctrl+I — курсив, Ctrl+Z — скасувати зміну.</p>
        <dl>
          <dt>Заголовок</dt><dd><code>## Назва розділу</code></dd>
          <dt>Жирний / курсив</dt><dd><code>**текст**</code> / <code>*текст*</code></dd>
          <dt>Список</dt><dd><code>- Пункт списку</code></dd>
          <dt>Посилання</dt><dd><code>[Назва](адреса)</code></dd>
          <dt>Таблиця</dt><dd>Кнопка «Таблиця» вставляє готовий шаблон.</dd>
          <dt>Код</dt><dd>Кнопка «Код» додає блок для прикладу коду.</dd>
        </dl>
      </details>
      <div ref="host" class="markdown-host"></div>
      <div class="markdown-status" :class="{'error-message': length > 20000}" aria-live="polite">
        {{ length.toLocaleString('uk-UA') }} / 20 000 символів
        <span v-if="length > 20000"> — скоротіть текст перед збереженням</span>
      </div>
    </section>`,
  props: { value: String },
  data() {
    return {
      preview: false,
      length: Array.from(this.value || "").length,
      tools: [
        {label: "Заголовок", command: "heading", args: {level: 2}, hint: "Заголовок розділу: ## Назва"},
        {label: "Жирний", command: "bold", hint: "Жирний текст: **текст** · Ctrl+B"},
        {label: "Курсив", command: "italic", hint: "Курсив: *текст* · Ctrl+I"},
        {label: "Список", command: "bulletList", hint: "Список: - Пункт"},
        {label: "Таблиця", command: "table", hint: "Вставити шаблон Markdown-таблиці"},
        {label: "Код", command: "codeBlock", hint: "Вставити блок коду"},
        {label: "Скасувати", command: "undo", hint: "Скасувати останню зміну · Ctrl+Z"},
        {label: "Повторити", command: "redo", hint: "Повторити скасовану зміну"},
      ],
    };
  },
  mounted() {
    this.editor = new toastui.Editor({
      el: this.$refs.host,
      initialValue: this.value || "",
      initialEditType: "markdown",
      previewStyle: "vertical",
      hideModeSwitch: true,
      toolbarItems: [],
      language: "uk-UA",
      height: "480px",
      usageStatistics: false,
      autofocus: false,
      events: {change: () => { this.length = Array.from(this.editor.getMarkdown()).length; }},
    });
    this.$refs.host.querySelector('.toastui-editor-md-container .ProseMirror')
      .setAttribute('aria-label', 'Текст інструкції Markdown');
    this.$refs.host.querySelector('.toastui-editor-md-container .ProseMirror')
      .setAttribute('role', 'textbox');
    this.$refs.host.querySelector('.toastui-editor-md-container .ProseMirror')
      .setAttribute('aria-multiline', 'true');
  },
  beforeUnmount() {
    this.editor?.destroy();
  },
  methods: {
    getMarkdown() { return this.editor.getMarkdown(); },
    format(tool) {
      this.editor.focus();
      if (tool.command === "table") {
        this.editor.insertText('\n| Поле | Опис |\n| --- | --- |\n| Назва | Пояснення |\n');
      } else {
        this.editor.exec(tool.command, tool.args);
      }
    },
  },
};
