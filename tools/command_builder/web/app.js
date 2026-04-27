(function () {
    const state = {
        step: 1,
        phrases: [""],
        cmdId: "",
        cmdIdAuto: true,
        existingIds: [],
        actionType: null,
        action: null,
        confirmSound: null,
    };

    const els = {
        steps: document.querySelectorAll(".step"),
        panels: document.querySelectorAll(".panel"),
        phrase0: document.getElementById("phrase-0"),
        extra: document.getElementById("extra-phrases"),
        addPhrase: document.getElementById("add-phrase"),
        cmdId: document.getElementById("cmd-id"),
        cmdIdHint: document.getElementById("cmd-id-hint"),
        actionGrid: document.getElementById("action-grid"),
        paramsForm: document.getElementById("params-form"),
        yamlPreview: document.getElementById("yaml-preview"),
        saveBtn: document.getElementById("save-btn"),
        cancelBtn: document.getElementById("cancel-btn"),
        saveStatus: document.getElementById("save-status"),
        toast: document.getElementById("toast"),
        toStep3: document.getElementById("to-step-3"),
        tabs: document.querySelectorAll(".tab"),
        tabContents: document.querySelectorAll("[data-tab-content]"),
        llmPrompt: document.getElementById("llm-prompt"),
        llmGenerate: document.getElementById("llm-generate"),
        llmStatus: document.getElementById("llm-status"),
        llmSuggestions: document.getElementById("llm-suggestions"),
    };

    function api() {
        return (window.pywebview && window.pywebview.api) || null;
    }

    async function callApi(method, ...args) {
        const a = api();
        if (!a || typeof a[method] !== "function") {
            return { ok: false, error: "bridge not ready: " + method };
        }
        try {
            return await a[method](...args);
        } catch (ex) {
            return { ok: false, error: String(ex) };
        }
    }

    function setStep(n) {
        state.step = n;
        els.panels.forEach((p) => {
            p.hidden = parseInt(p.dataset.panel, 10) !== n;
        });
        els.steps.forEach((s) => {
            s.classList.toggle("active", parseInt(s.dataset.step, 10) === n);
        });
        if (n === 4) {
            renderPreview();
        }
    }

    function showToast(msg, isError) {
        els.toast.textContent = msg;
        els.toast.classList.toggle("error", !!isError);
        els.toast.hidden = false;
        clearTimeout(showToast._t);
        showToast._t = setTimeout(() => { els.toast.hidden = true; }, 2800);
    }

    function refreshExtraPhrases() {
        els.extra.innerHTML = "";
        for (let i = 1; i < state.phrases.length; i++) {
            const row = document.createElement("div");
            row.className = "extra-row";
            const inp = document.createElement("input");
            inp.type = "text";
            inp.value = state.phrases[i];
            inp.placeholder = "синоним";
            inp.addEventListener("input", () => {
                state.phrases[i] = inp.value;
            });
            const rm = document.createElement("button");
            rm.type = "button";
            rm.textContent = "удалить";
            rm.addEventListener("click", () => {
                state.phrases.splice(i, 1);
                refreshExtraPhrases();
            });
            row.appendChild(inp);
            row.appendChild(rm);
            els.extra.appendChild(row);
        }
    }

    function transliterateSlug(s) {
        const map = {
            "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh",
            "з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o",
            "п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts",
            "ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
        };
        let out = "";
        const lower = (s || "").toLowerCase().trim();
        for (const ch of lower) {
            if (map[ch] !== undefined) out += map[ch];
            else if (/[a-z0-9]/i.test(ch)) out += ch;
            else if (ch === " " || ch === "_" || ch === "-") out += "_";
        }
        out = out.replace(/_+/g, "_").replace(/^_|_$/g, "");
        return out || "cmd";
    }

    function checkCmdIdCollision() {
        if (!state.cmdId) {
            els.cmdIdHint.className = "row-hint";
            els.cmdIdHint.textContent = "";
            return;
        }
        if (state.existingIds.includes(state.cmdId)) {
            els.cmdIdHint.className = "row-hint error";
            els.cmdIdHint.textContent = `Идентификатор «${state.cmdId}» уже используется`;
        } else {
            els.cmdIdHint.className = "row-hint ok";
            els.cmdIdHint.textContent = "Свободен";
        }
    }

    function syncCmdId() {
        if (state.cmdIdAuto) {
            state.cmdId = transliterateSlug(state.phrases[0] || "");
            els.cmdId.value = state.cmdId;
        }
        checkCmdIdCollision();
    }

    function renderActionForm() {
        const t = state.actionType;
        const f = els.paramsForm;
        f.innerHTML = "";
        if (!t) {
            f.innerHTML = `<p class="hint">Сначала выберите тип на шаге 2.</p>`;
            return;
        }

        if (t === "exe") {
            const wrap = document.createElement("div");
            wrap.innerHTML = `
                <div class="field">
                    <label>Файл из custom-commands/</label>
                    <select id="exe-file"><option value="">— выбрать —</option></select>
                </div>
                <div class="params-row">
                    <div class="field">
                        <label>Задержка после запуска (мс)</label>
                        <input type="number" id="exe-delay" min="0" step="50" placeholder="0">
                    </div>
                </div>
                <label class="checkbox"><input type="checkbox" id="exe-wait"> ждать завершения</label>
                <div class="row-hint" id="exe-hint"></div>
            `;
            f.appendChild(wrap);
            const sel = wrap.querySelector("#exe-file");
            callApi("list_exes").then((list) => {
                if (Array.isArray(list)) {
                    for (const name of list) {
                        const o = document.createElement("option");
                        o.value = `${name}.exe`;
                        o.textContent = name;
                        sel.appendChild(o);
                    }
                    if (state.action && state.action.file) sel.value = state.action.file;
                }
            });
            sel.addEventListener("change", () => updateAction());
            wrap.querySelector("#exe-delay").addEventListener("input", () => updateAction());
            wrap.querySelector("#exe-wait").addEventListener("change", () => updateAction());
            if (state.action) {
                wrap.querySelector("#exe-delay").value = state.action.delay_ms ?? "";
                wrap.querySelector("#exe-wait").checked = !!state.action.wait;
            }
            return;
        }

        if (t === "url") {
            f.innerHTML = `
                <div class="field">
                    <label>URL</label>
                    <input type="text" id="url-href" placeholder="https://example.com">
                </div>
                <div class="field">
                    <label>Браузер</label>
                    <select id="url-browser">
                        <option value="">по умолчанию (системный)</option>
                        <option value="yandex">Yandex Browser</option>
                        <option value="chrome">Google Chrome</option>
                        <option value="firefox">Mozilla Firefox</option>
                        <option value="edge">Microsoft Edge</option>
                    </select>
                </div>
            `;
            const inp = f.querySelector("#url-href");
            const sel = f.querySelector("#url-browser");
            if (state.action) {
                inp.value = state.action.href || "";
                sel.value = state.action.browser || "";
            }
            inp.addEventListener("input", () => updateAction());
            sel.addEventListener("change", () => updateAction());
            return;
        }

        if (t === "keys") {
            f.innerHTML = `
                <div class="field">
                    <label>Режим</label>
                    <select id="keys-mode">
                        <option value="sequence">Сочетание клавиш</option>
                        <option value="text">Печатать текст</option>
                    </select>
                </div>
                <div class="field" id="keys-seq-field">
                    <label>Сочетание</label>
                    <input type="text" id="keys-sequence" placeholder="ctrl+shift+m">
                    <div class="row-hint">Разделяйте плюсом. Пример: ctrl+alt+delete</div>
                </div>
                <div class="field" id="keys-text-field" hidden>
                    <label>Текст</label>
                    <input type="text" id="keys-text" placeholder="Привет, мир">
                </div>
            `;
            const mode = f.querySelector("#keys-mode");
            const seqField = f.querySelector("#keys-seq-field");
            const textField = f.querySelector("#keys-text-field");
            const seq = f.querySelector("#keys-sequence");
            const text = f.querySelector("#keys-text");
            if (state.action && state.action.text) {
                mode.value = "text";
                text.value = state.action.text;
                seqField.hidden = true;
                textField.hidden = false;
            } else if (state.action && state.action.sequence) {
                seq.value = state.action.sequence;
            }
            const sync = () => {
                if (mode.value === "sequence") {
                    seqField.hidden = false;
                    textField.hidden = true;
                } else {
                    seqField.hidden = true;
                    textField.hidden = false;
                }
                updateAction();
            };
            mode.addEventListener("change", sync);
            seq.addEventListener("input", () => updateAction());
            text.addEventListener("input", () => updateAction());
            return;
        }

        if (t === "play_sound") {
            f.innerHTML = `
                <div class="params-row">
                    <div class="field">
                        <label>Имя звука</label>
                        <select id="snd-name"></select>
                    </div>
                    <button type="button" class="ghost" id="snd-preview">прослушать</button>
                </div>
            `;
            const sel = f.querySelector("#snd-name");
            callApi("list_sound_names").then((list) => {
                if (Array.isArray(list)) {
                    for (const name of list) {
                        const o = document.createElement("option");
                        o.value = name;
                        o.textContent = name;
                        sel.appendChild(o);
                    }
                    if (state.action && state.action.name) sel.value = state.action.name;
                    updateAction();
                }
            });
            sel.addEventListener("change", () => updateAction());
            f.querySelector("#snd-preview").addEventListener("click", () => {
                callApi("preview_sound", sel.value);
            });
            return;
        }

        if (t === "system") {
            f.innerHTML = `
                <div class="field">
                    <label>Операция</label>
                    <select id="sys-op">
                        <option value="volume_mute">Выключить звук</option>
                        <option value="volume_unmute">Включить звук</option>
                        <option value="exit">Выгрузить Jarvis</option>
                    </select>
                </div>
            `;
            const sel = f.querySelector("#sys-op");
            if (state.action && state.action.op) sel.value = state.action.op;
            sel.addEventListener("change", () => updateAction());
            return;
        }

        if (t === "shell") {
            f.innerHTML = `
                <div class="field">
                    <label>Команда (PowerShell)</label>
                    <textarea id="shell-cmd" rows="3" placeholder="Get-Process | Select-Object -First 5"></textarea>
                </div>
                <label class="checkbox"><input type="checkbox" id="shell-wait"> ждать завершения</label>
            `;
            const cmd = f.querySelector("#shell-cmd");
            const wait = f.querySelector("#shell-wait");
            if (state.action) {
                cmd.value = state.action.cmd || "";
                wait.checked = !!state.action.wait;
            }
            cmd.addEventListener("input", () => updateAction());
            wait.addEventListener("change", () => updateAction());
            return;
        }

        if (t === "sleep") {
            f.innerHTML = `
                <div class="field">
                    <label>Длительность (мс)</label>
                    <input type="number" id="sleep-ms" min="0" step="50" value="500">
                </div>
                <div class="row-hint">Обычно используется внутри последовательности.</div>
            `;
            const inp = f.querySelector("#sleep-ms");
            if (state.action && state.action.ms != null) inp.value = state.action.ms;
            inp.addEventListener("input", () => updateAction());
            return;
        }

        if (t === "multi") {
            renderMultiForm();
            return;
        }
    }

    function renderMultiForm() {
        const f = els.paramsForm;
        f.innerHTML = `
            <p class="hint">Шаги выполняются по порядку.</p>
            <div class="steps-list" id="steps-list"></div>
            <button type="button" class="ghost" id="add-step">+ шаг</button>
        `;
        const list = f.querySelector("#steps-list");
        if (!state.action || state.action.type !== "multi") {
            state.action = { type: "multi", steps: [] };
        }
        const renderList = () => {
            list.innerHTML = "";
            state.action.steps.forEach((step, idx) => {
                const card = document.createElement("div");
                card.className = "step-card";
                card.innerHTML = `
                    <div class="step-head">
                        <span class="step-label">Шаг ${idx + 1}</span>
                        <div>
                            <button type="button" class="icon-btn" data-up>↑</button>
                            <button type="button" class="icon-btn" data-down>↓</button>
                            <button type="button" class="icon-btn" data-rm>удалить</button>
                        </div>
                    </div>
                `;
                const body = document.createElement("div");
                renderInlineEditor(body, step, (next) => {
                    state.action.steps[idx] = next;
                    updateAction(true);
                });
                card.appendChild(body);
                card.querySelector("[data-up]").addEventListener("click", () => {
                    if (idx > 0) {
                        const tmp = state.action.steps[idx - 1];
                        state.action.steps[idx - 1] = state.action.steps[idx];
                        state.action.steps[idx] = tmp;
                        renderList();
                        updateAction(true);
                    }
                });
                card.querySelector("[data-down]").addEventListener("click", () => {
                    if (idx < state.action.steps.length - 1) {
                        const tmp = state.action.steps[idx + 1];
                        state.action.steps[idx + 1] = state.action.steps[idx];
                        state.action.steps[idx] = tmp;
                        renderList();
                        updateAction(true);
                    }
                });
                card.querySelector("[data-rm]").addEventListener("click", () => {
                    state.action.steps.splice(idx, 1);
                    renderList();
                    updateAction(true);
                });
                list.appendChild(card);
            });
        };
        renderList();
        f.querySelector("#add-step").addEventListener("click", () => {
            state.action.steps.push({ type: "play_sound", name: "ok" });
            renderList();
            updateAction(true);
        });
        updateAction(true);
    }

    function renderInlineEditor(host, step, onChange) {
        const typeSel = document.createElement("select");
        const types = [
            ["play_sound", "Звук"],
            ["exe", ".exe"],
            ["url", "URL"],
            ["keys", "Клавиши"],
            ["shell", "Shell"],
            ["system", "Система"],
            ["sleep", "Пауза"],
        ];
        for (const [v, label] of types) {
            const o = document.createElement("option");
            o.value = v;
            o.textContent = label;
            if (v === step.type) o.selected = true;
            typeSel.appendChild(o);
        }
        host.appendChild(wrapField("Тип", typeSel));

        const body = document.createElement("div");
        host.appendChild(body);

        const renderBody = () => {
            body.innerHTML = "";
            const t = typeSel.value;
            if (t === "play_sound") {
                const sel = document.createElement("select");
                callApi("list_sound_names").then((list) => {
                    if (Array.isArray(list)) {
                        for (const name of list) {
                            const o = document.createElement("option");
                            o.value = name;
                            o.textContent = name;
                            if (step.name === name) o.selected = true;
                            sel.appendChild(o);
                        }
                    }
                });
                sel.addEventListener("change", () => onChange({ type: "play_sound", name: sel.value }));
                body.appendChild(wrapField("Звук", sel));
            } else if (t === "exe") {
                const sel = document.createElement("select");
                callApi("list_exes").then((list) => {
                    if (Array.isArray(list)) {
                        for (const name of list) {
                            const o = document.createElement("option");
                            o.value = `${name}.exe`;
                            o.textContent = name;
                            if (step.file === `${name}.exe`) o.selected = true;
                            sel.appendChild(o);
                        }
                    }
                });
                const wait = document.createElement("input");
                wait.type = "checkbox";
                wait.checked = !!step.wait;
                const waitLabel = document.createElement("label");
                waitLabel.className = "checkbox";
                waitLabel.appendChild(wait);
                waitLabel.appendChild(document.createTextNode("ждать"));
                const delay = document.createElement("input");
                delay.type = "number";
                delay.value = step.delay_ms ?? "";
                delay.placeholder = "delay_ms";
                const apply = () => {
                    const next = { type: "exe", file: sel.value };
                    if (wait.checked) next.wait = true;
                    if (delay.value) next.delay_ms = parseInt(delay.value, 10);
                    onChange(next);
                };
                sel.addEventListener("change", apply);
                wait.addEventListener("change", apply);
                delay.addEventListener("input", apply);
                body.appendChild(wrapField("Файл", sel));
                body.appendChild(wrapField("Задержка (мс)", delay));
                body.appendChild(waitLabel);
            } else if (t === "url") {
                const inp = document.createElement("input");
                inp.type = "text";
                inp.value = step.href || "";
                inp.placeholder = "https://...";
                const sel = document.createElement("select");
                sel.innerHTML = `
                    <option value="">по умолчанию (системный)</option>
                    <option value="yandex">Yandex Browser</option>
                    <option value="chrome">Google Chrome</option>
                    <option value="firefox">Mozilla Firefox</option>
                    <option value="edge">Microsoft Edge</option>`;
                sel.value = step.browser || "";
                const apply = () => {
                    const next = { type: "url", href: inp.value };
                    if (sel.value) next.browser = sel.value;
                    onChange(next);
                };
                inp.addEventListener("input", apply);
                sel.addEventListener("change", apply);
                body.appendChild(wrapField("URL", inp));
                body.appendChild(wrapField("Браузер", sel));
            } else if (t === "keys") {
                const inp = document.createElement("input");
                inp.type = "text";
                inp.value = step.sequence || "";
                inp.placeholder = "ctrl+shift+m";
                inp.addEventListener("input", () => onChange({ type: "keys", sequence: inp.value }));
                body.appendChild(wrapField("Сочетание", inp));
            } else if (t === "shell") {
                const inp = document.createElement("input");
                inp.type = "text";
                inp.value = step.cmd || "";
                const wait = document.createElement("input");
                wait.type = "checkbox";
                wait.checked = !!step.wait;
                const waitLabel = document.createElement("label");
                waitLabel.className = "checkbox";
                waitLabel.appendChild(wait);
                waitLabel.appendChild(document.createTextNode("ждать"));
                const apply = () => {
                    const next = { type: "shell", cmd: inp.value };
                    if (wait.checked) next.wait = true;
                    onChange(next);
                };
                inp.addEventListener("input", apply);
                wait.addEventListener("change", apply);
                body.appendChild(wrapField("Команда", inp));
                body.appendChild(waitLabel);
            } else if (t === "system") {
                const sel = document.createElement("select");
                for (const op of ["volume_mute", "volume_unmute", "exit"]) {
                    const o = document.createElement("option");
                    o.value = op;
                    o.textContent = op;
                    if (step.op === op) o.selected = true;
                    sel.appendChild(o);
                }
                sel.addEventListener("change", () => onChange({ type: "system", op: sel.value }));
                body.appendChild(wrapField("Операция", sel));
            } else if (t === "sleep") {
                const inp = document.createElement("input");
                inp.type = "number";
                inp.value = step.ms ?? 500;
                inp.addEventListener("input", () => onChange({ type: "sleep", ms: parseInt(inp.value, 10) || 0 }));
                body.appendChild(wrapField("Миллисекунды", inp));
            }
        };
        typeSel.addEventListener("change", () => {
            const t = typeSel.value;
            const fresh = ({
                play_sound: { type: "play_sound", name: "ok" },
                exe: { type: "exe", file: "" },
                url: { type: "url", href: "" },
                keys: { type: "keys", sequence: "" },
                shell: { type: "shell", cmd: "" },
                system: { type: "system", op: "volume_mute" },
                sleep: { type: "sleep", ms: 500 },
            })[t];
            onChange(fresh);
            step = fresh;
            renderBody();
        });
        renderBody();
    }

    function wrapField(label, control) {
        const w = document.createElement("div");
        w.className = "field";
        const l = document.createElement("label");
        l.textContent = label;
        w.appendChild(l);
        w.appendChild(control);
        return w;
    }

    function updateAction(skipRender) {
        const t = state.actionType;
        if (!t) return;
        if (t === "exe") {
            const file = document.getElementById("exe-file");
            const delay = document.getElementById("exe-delay");
            const wait = document.getElementById("exe-wait");
            const a = { type: "exe", file: file ? file.value : "" };
            if (wait && wait.checked) a.wait = true;
            if (delay && delay.value) a.delay_ms = parseInt(delay.value, 10);
            state.action = a;
        } else if (t === "url") {
            const a = { type: "url", href: (document.getElementById("url-href")||{}).value || "" };
            const b = (document.getElementById("url-browser")||{}).value;
            if (b) a.browser = b;
            state.action = a;
        } else if (t === "keys") {
            const mode = (document.getElementById("keys-mode")||{}).value;
            if (mode === "text") {
                state.action = { type: "keys", text: (document.getElementById("keys-text")||{}).value || "" };
            } else {
                state.action = { type: "keys", sequence: (document.getElementById("keys-sequence")||{}).value || "" };
            }
        } else if (t === "play_sound") {
            state.action = { type: "play_sound", name: (document.getElementById("snd-name")||{}).value || "ok" };
        } else if (t === "system") {
            state.action = { type: "system", op: (document.getElementById("sys-op")||{}).value || "volume_mute" };
        } else if (t === "shell") {
            const a = { type: "shell", cmd: (document.getElementById("shell-cmd")||{}).value || "" };
            if ((document.getElementById("shell-wait")||{}).checked) a.wait = true;
            state.action = a;
        } else if (t === "sleep") {
            state.action = { type: "sleep", ms: parseInt((document.getElementById("sleep-ms")||{}).value || "0", 10) };
        }
    }

    function buildDraft() {
        return {
            cmd_id: state.cmdId,
            phrases: state.phrases.map((p) => p.trim()).filter(Boolean),
            action: state.action,
            confirm_sound: state.confirmSound || undefined,
        };
    }

    function renderPreview() {
        const draft = buildDraft();
        if (!draft.cmd_id || !draft.phrases.length || !draft.action) {
            els.yamlPreview.textContent = "(черновик неполный)";
            return;
        }
        const body = { phrases: draft.phrases, action: draft.action };
        if (draft.confirm_sound) body.confirm_sound = draft.confirm_sound;
        const obj = {};
        obj[draft.cmd_id] = body;
        try {
            els.yamlPreview.textContent = jsyaml.dump(obj, { lineWidth: 4096, noRefs: true });
        } catch (ex) {
            els.yamlPreview.textContent = "Ошибка YAML: " + ex.message;
        }
    }

    async function refreshExistingIds() {
        const r = await callApi("list_existing_commands");
        if (Array.isArray(r)) {
            state.existingIds = r;
            checkCmdIdCollision();
        }
    }

    function bind() {
        els.phrase0.addEventListener("input", () => {
            state.phrases[0] = els.phrase0.value;
            syncCmdId();
        });
        els.addPhrase.addEventListener("click", () => {
            state.phrases.push("");
            refreshExtraPhrases();
        });
        els.cmdId.addEventListener("input", () => {
            state.cmdIdAuto = false;
            state.cmdId = els.cmdId.value.trim();
            checkCmdIdCollision();
        });

        els.actionGrid.addEventListener("click", (ev) => {
            const card = ev.target.closest(".card");
            if (!card) return;
            const t = card.dataset.action;
            els.actionGrid.querySelectorAll(".card").forEach((c) => c.classList.toggle("selected", c === card));
            if (state.actionType !== t) {
                state.actionType = t;
                state.action = null;
            }
        });

        els.toStep3.addEventListener("click", () => {
            if (!state.actionType) {
                showToast("Выберите тип действия", true);
                return;
            }
            renderActionForm();
            setStep(3);
        });

        document.querySelectorAll("[data-go]").forEach((b) => {
            if (b.id === "to-step-3") return;
            b.addEventListener("click", () => setStep(parseInt(b.dataset.go, 10)));
        });

        els.steps.forEach((s) => {
            s.addEventListener("click", () => {
                const target = parseInt(s.dataset.step, 10);
                if (target === 3) renderActionForm();
                setStep(target);
            });
        });

        els.tabs.forEach((t) => {
            t.addEventListener("click", () => {
                els.tabs.forEach((x) => x.classList.toggle("active", x === t));
                els.tabContents.forEach((c) => {
                    c.hidden = c.dataset.tabContent !== t.dataset.tab;
                });
            });
        });

        els.llmGenerate.addEventListener("click", async () => {
            els.llmStatus.className = "row-hint";
            els.llmStatus.textContent = "Запрос к модели...";
            els.llmSuggestions.innerHTML = "";
            const r = await callApi("llm_suggest", els.llmPrompt.value || "");
            if (!r || !r.ok) {
                els.llmStatus.className = "row-hint error";
                els.llmStatus.textContent = (r && r.error) || "Не удалось получить ответ";
                return;
            }
            els.llmStatus.className = "row-hint ok";
            els.llmStatus.textContent = "Готово. Примите блок или отредактируйте вручную.";
            renderLlmSuggestion(r.suggestion);
        });

        els.saveBtn.addEventListener("click", async () => {
            const draft = buildDraft();
            const v = await callApi("validate_draft", JSON.stringify(draft));
            if (!v.ok) {
                els.saveStatus.className = "row-hint error";
                els.saveStatus.textContent = v.error;
                return;
            }
            const overwrite = state.existingIds.includes(draft.cmd_id);
            if (overwrite) {
                if (!confirm(`Команда «${draft.cmd_id}» уже существует. Перезаписать?`)) return;
                draft.overwrite = true;
            }
            const r = await callApi("save_command", JSON.stringify(draft));
            if (!r.ok) {
                els.saveStatus.className = "row-hint error";
                els.saveStatus.textContent = r.error;
                return;
            }
            els.saveStatus.className = "row-hint ok";
            els.saveStatus.textContent = `Сохранено: ${r.id}`;
            showToast(`Команда «${r.id}» сохранена`);
            refreshExistingIds();
        });

        els.cancelBtn.addEventListener("click", () => {
            if (!confirm("Сбросить черновик?")) return;
            resetDraft();
        });

        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Escape") {
                if (state.step > 1) setStep(state.step - 1);
                return;
            }
            if (ev.key === "Enter" && !ev.shiftKey && !ev.ctrlKey && !ev.altKey) {
                const tag = (ev.target && ev.target.tagName) || "";
                if (tag === "TEXTAREA") return;
                if (tag === "BUTTON") return;
                if (state.step < 4) {
                    if (state.step === 2 && state.actionType) renderActionForm();
                    setStep(state.step + 1);
                    ev.preventDefault();
                }
            }
        });
    }

    function renderLlmSuggestion(suggestion) {
        const host = els.llmSuggestions;
        host.innerHTML = "";
        if (!suggestion) return;
        const block = document.createElement("div");
        block.className = "suggested-block";
        const pre = document.createElement("pre");
        try {
            pre.textContent = jsyaml.dump(suggestion, { lineWidth: 4096, noRefs: true });
        } catch (ex) {
            pre.textContent = JSON.stringify(suggestion, null, 2);
        }
        block.appendChild(pre);
        const accept = document.createElement("button");
        accept.type = "button";
        accept.className = "primary";
        accept.textContent = "Принять";
        accept.addEventListener("click", () => {
            if (suggestion.phrases) state.phrases = suggestion.phrases.slice();
            if (suggestion.cmd_id) {
                state.cmdId = suggestion.cmd_id;
                state.cmdIdAuto = false;
                els.cmdId.value = state.cmdId;
            } else {
                syncCmdId();
            }
            els.phrase0.value = state.phrases[0] || "";
            refreshExtraPhrases();
            if (suggestion.action) {
                state.actionType = suggestion.action.type;
                state.action = suggestion.action;
                els.actionGrid.querySelectorAll(".card").forEach((c) => {
                    c.classList.toggle("selected", c.dataset.action === state.actionType);
                });
                els.tabs.forEach((x) => x.classList.toggle("active", x.dataset.tab === "manual"));
                els.tabContents.forEach((c) => { c.hidden = c.dataset.tabContent !== "manual"; });
                renderActionForm();
            }
            setStep(3);
        });
        const discard = document.createElement("button");
        discard.type = "button";
        discard.className = "ghost";
        discard.textContent = "Отклонить";
        discard.addEventListener("click", () => { host.innerHTML = ""; });
        const actions = document.createElement("div");
        actions.className = "actions";
        actions.appendChild(discard);
        actions.appendChild(accept);
        block.appendChild(actions);
        host.appendChild(block);
    }

    function resetDraft() {
        state.phrases = [""];
        state.cmdId = "";
        state.cmdIdAuto = true;
        state.actionType = null;
        state.action = null;
        state.confirmSound = null;
        els.phrase0.value = "";
        els.cmdId.value = "";
        els.cmdIdHint.textContent = "";
        refreshExtraPhrases();
        els.actionGrid.querySelectorAll(".card").forEach((c) => c.classList.remove("selected"));
        els.paramsForm.innerHTML = "";
        els.yamlPreview.textContent = "";
        els.saveStatus.textContent = "";
        setStep(1);
    }

    function init() {
        bind();
        refreshExtraPhrases();
        setStep(1);
        const tryReady = () => {
            if (api()) {
                refreshExistingIds();
            } else {
                setTimeout(tryReady, 80);
            }
        };
        tryReady();
    }

    document.addEventListener("DOMContentLoaded", init);
})();
