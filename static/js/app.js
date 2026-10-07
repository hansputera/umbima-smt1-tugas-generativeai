/* Generic client-side filters (parity with Node inline state). */
function nilaiFilter(e) {
  var t = e.target;
  if (!t || !t.getAttribute) return;
  var rowsSel = t.getAttribute("data-filter-select");
  var textSel = t.getAttribute("data-filter-rows");
  if (rowsSel) {
    var rows = document.querySelectorAll(rowsSel);
    var val = t.value;
    var shown = 0;
    rows.forEach(function (r) {
      var match =
        val === "all" ||
        r.getAttribute("data-value") === val ||
        r.getAttribute("data-period") === val;
      r.style.display = match ? "" : "none";
      if (match) shown += 1;
    });
    var counter = t.getAttribute("data-counter");
    if (counter) {
      var el = document.querySelector(counter);
      if (el) el.textContent = shown + " dari " + rows.length + " kelas";
    }
  } else if (textSel) {
    var box = document.querySelector(textSel);
    if (!box) return;
    var q = (t.value || "").trim().toLowerCase();
    var items = box.querySelectorAll("[data-search]");
    var visible = 0;
    items.forEach(function (el) {
      var hay = (el.getAttribute("data-search") || "").toLowerCase();
      var match = !q || hay.indexOf(q) !== -1;
      el.style.display = match ? "" : "none";
      var wrap = el.parentElement;
      if (wrap && wrap.tagName === "FORM") wrap.style.display = match ? "" : "none";
      if (match) visible += 1;
    });
    var empty = box.querySelector("[data-empty]");
    if (empty) empty.style.display = visible === 0 ? "" : "none";
    var cSel = t.getAttribute("data-counter");
    if (cSel) {
      var c = document.querySelector(cSel);
      if (c) c.textContent = visible + " dari " + items.length + " kelas";
    }
  }
}
document.addEventListener("input", nilaiFilter);
document.addEventListener("change", nilaiFilter);

/* Settings: mark key fields dirty (submit name) and hide the "kosongkan" hint. */
document.addEventListener("input", function (e) {
  var t = e.target;
  if (!t || !t.matches || !t.matches("[data-key-name]")) return;
  if (!t.name) t.name = t.getAttribute("data-key-name");
  var field = t.closest(".field");
  var hint = field && field.querySelector("[data-dirty-hide]");
  if (hint) hint.style.display = "none";
});

/* Settings: reveal/hide the real API key (Node revealApiKey parity). */
document.addEventListener("click", function (e) {
  var btn = e.target.closest && e.target.closest("[data-reveal]");
  if (!btn) return;
  var input = document.getElementById(btn.getAttribute("data-reveal"));
  if (!input) return;
  var label = btn.querySelector("[data-reveal-label]") || btn;
  if (input.dataset.shown === "1") {
    input.type = "password";
    input.dataset.shown = "0";
    label.textContent = "Reveal";
    return;
  }
  var token = document.querySelector("[name=csrfmiddlewaretoken]");
  fetch("/admin/settings/reveal", {
    method: "POST",
    headers: {
      "X-CSRFToken": token ? token.value : "",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: new URLSearchParams({ key: btn.getAttribute("data-reveal") }),
  })
    .then(function (r) {
      return r.text();
    })
    .then(function (text) {
      input.value = text;
      input.type = "text";
      input.dataset.shown = "1";
      label.textContent = "Sembunyikan";
    });
});

/* ============================================================
   Phase 4 — course index toggle + topic detail list editors
   ============================================================ */

document.addEventListener("click", function (e) {
  var btn = e.target.closest && e.target.closest("[data-index-toggle]");
  if (btn) {
    var layout = document.getElementById("course-layout");
    if (!layout) return;
    if (btn.getAttribute("data-index-toggle") === "hide") {
      layout.classList.add("index-hidden");
    } else {
      layout.classList.remove("index-hidden");
    }
    return;
  }

  var addBtn = e.target.closest && e.target.closest("[data-list-add]");
  if (addBtn) {
    var key = addBtn.getAttribute("data-list-add");
    var tpl = document.querySelector('template[data-list-template="' + key + '"]');
    var rows = document.querySelector('[data-list-rows="' + key + '"]');
    if (!tpl || !rows) return;
    rows.appendChild(tpl.content.firstElementChild.cloneNode(true));
    rows.hidden = false;
    var empty = document.querySelector('[data-list-empty="' + key + '"]');
    if (empty) empty.hidden = true;
    renumberRows(key);
    return;
  }

  var rmBtn = e.target.closest && e.target.closest("[data-list-remove]");
  if (rmBtn) {
    var rkey = rmBtn.getAttribute("data-list-remove");
    var rrows = document.querySelector('[data-list-rows="' + rkey + '"]');
    var rowSel = rkey === "pg" ? "[data-question-row]" : "[data-block-row]";
    var row = rmBtn.closest(rowSel);
    if (!rrows || !row) return;
    row.remove();
    renumberRows(rkey);
    if (rkey !== "pg") {
      var has = rrows.querySelectorAll("[data-block-row]").length > 0;
      rrows.hidden = !has;
      var rempty = document.querySelector('[data-list-empty="' + rkey + '"]');
      if (rempty) rempty.hidden = has;
    }
    return;
  }

  var optBtn = e.target.closest && e.target.closest("[data-add-option]");
  if (optBtn) {
    var qrow = optBtn.closest("[data-question-row]");
    if (!qrow) return;
    var olist = qrow.querySelector("[data-option-list]");
    if (!olist) return;
    var count = olist.querySelectorAll("[data-option-row]").length;
    if (count >= 6) return;
    var okey = String.fromCharCode(65 + count);
    var orow = document.createElement("div");
    orow.className = "option-row";
    orow.setAttribute("data-option-row", "");
    orow.innerHTML =
      '<input class="radio" type="radio" data-q-answer data-aria-text="Kunci soal {n}: {key}" value="' +
      okey +
      '"><span class="option-letter">' +
      okey +
      '</span><input class="input" data-option-text placeholder="Opsi ' +
      okey +
      '" value="">';
    olist.appendChild(orow);
    if (count + 1 >= 6) optBtn.parentElement.hidden = true;
    var n = Array.prototype.indexOf.call(
      olist.closest("[data-list-rows]").querySelectorAll("[data-question-row]"),
      qrow
    ) + 1;
    orow.querySelectorAll("[data-q-answer]").forEach(function (r) {
      r.name = "answer_key_" + n;
      r.setAttribute("aria-label", "Kunci soal " + n + ": " + okey);
    });
  }
});

function renumberRows(key) {
  var rows = document.querySelector('[data-list-rows="' + key + '"]');
  if (!rows) return;
  var rowSel = key === "pg" ? "[data-question-row]" : "[data-block-row]";
  var list = rows.querySelectorAll(rowSel);
  list.forEach(function (row, i) {
    var n = i + 1;
    row.querySelectorAll("[data-renumber-text]").forEach(function (el) {
      el.textContent = el.getAttribute("data-renumber-text").replace("{n}", n);
    });
    row.querySelectorAll("[data-aria-text]").forEach(function (el) {
      var label = el.getAttribute("data-aria-text").replace("{n}", n);
      if (el.type === "radio") label = label.replace("{key}", el.value);
      el.setAttribute("aria-label", label);
    });
    row.querySelectorAll("[data-q-answer]").forEach(function (r) {
      r.name = "answer_key_" + n;
    });
    var rm = row.querySelector("[data-list-remove]");
    if (rm && key === "pg") rm.hidden = list.length <= 1;
  });
}

document.addEventListener("change", function (e) {
  var t = e.target;
  if (!t || !t.matches) return;
  if (t.matches("[data-block-type]")) {
    var row = t.closest("[data-block-row]");
    if (!row) return;
    row.setAttribute("data-type", t.value);
    row.querySelectorAll("[data-block-for]").forEach(function (f) {
      f.hidden = f.getAttribute("data-block-for") !== t.value;
    });
  } else if (t.matches("[data-block-file]")) {
    var frow = t.closest("[data-block-row]");
    var file = t.files && t.files[0];
    if (frow && file) {
      frow.setAttribute("data-file-name", file.name);
      var span = frow.querySelector("[data-block-name]");
      if (span) span.textContent = file.name;
    }
  } else if (t.matches("[data-assign-type]")) {
    var want = t.value === "pg" ? "pg" : "nonpg";
    document.querySelectorAll("[data-assign-for]").forEach(function (el) {
      el.hidden = el.getAttribute("data-assign-for") !== want;
    });
  }
});

function serializeBlocks() {
  var out = [];
  document.querySelectorAll("[data-block-row]").forEach(function (row) {
    var type = row.getAttribute("data-type") || "richtext";
    var field = row.querySelector('[data-block-for="' + type + '"]');
    if (type === "link") {
      var body = field && field.querySelector("[data-block-body]");
      var url = field && field.querySelector("[data-block-url]");
      out.push({ type: "link", body: body ? body.value : "", url: url ? url.value : "" });
    } else if (type === "file") {
      out.push({ type: "file", file_name: row.getAttribute("data-file-name") || "" });
    } else {
      var ta = field && field.querySelector("[data-block-body]");
      out.push({ type: "richtext", body: ta ? ta.value : "" });
    }
  });
  return JSON.stringify(out);
}

function serializeQuestions() {
  var out = [];
  document.querySelectorAll("[data-question-row]").forEach(function (row) {
    var ta = row.querySelector("[data-q-text]");
    var opts = [];
    var answer = "";
    row.querySelectorAll("[data-option-row]").forEach(function (orow) {
      var radio = orow.querySelector("[data-q-answer]");
      var input = orow.querySelector("[data-option-text]");
      if (!radio || !input) return;
      if (radio.checked) answer = radio.value;
      if (radio.value && input.value.trim()) {
        opts.push({ key: radio.value, text: input.value });
      }
    });
    out.push({
      question: ta ? ta.value : "",
      options: opts,
      answer_key: answer,
    });
  });
  return JSON.stringify(out);
}

document.addEventListener("submit", function (e) {
  var form = e.target;
  if (!form || !form.id) return;
  if (form.id === "topic-form") {
    var blocksEl = document.getElementById("blocks-json");
    if (blocksEl) blocksEl.value = serializeBlocks();
  } else if (form.id === "assign-form") {
    var typeSel = document.getElementById("a-type");
    var qEl = document.getElementById("questions-json");
    if (qEl) {
      qEl.value = typeSel && typeSel.value === "pg" ? serializeQuestions() : "[]";
    }
  }
});

// ---- Assignment detail: rubric editor + release mode ----
(function () {
  var rubForm = document.querySelector("[data-rubric]");
  if (rubForm) {
    var body = rubForm.querySelector("[data-rubric-body]");
    var tableWrap = rubForm.querySelector("[data-rubric-table]");
    var emptyEl = rubForm.querySelector("[data-rubric-empty]");
    var totalEl = rubForm.querySelector("[data-rubric-total]");
    var submitBtn = rubForm.querySelector("[data-rubric-submit]");
    var criteriaInput = document.getElementById("criteria-json");
    var tpl = rubForm.querySelector("[data-rubric-template]");

    function rowList() {
      return Array.prototype.slice.call(
        body.querySelectorAll("[data-rubric-row]")
      );
    }

    function serializeRubric() {
      var out = rowList().map(function (tr) {
        function f(name) {
          return tr.querySelector('[data-f="' + name + '"]');
        }
        var nameEl = f("name");
        var weightEl = f("weight");
        return {
          id: tr.getAttribute("data-id") || null,
          name: nameEl ? nameEl.value : "",
          weight: weightEl ? Number(weightEl.value) || 0 : 0,
          level_1: f("level_1") ? f("level_1").value : "",
          level_2: f("level_2") ? f("level_2").value : "",
          level_3: f("level_3") ? f("level_3").value : "",
          level_4: f("level_4") ? f("level_4").value : "",
          prompt_notes: f("prompt_notes") ? f("prompt_notes").value : "",
        };
      });
      if (criteriaInput) criteriaInput.value = JSON.stringify(out);
      return out;
    }

    function renumberRubric() {
      rowList().forEach(function (tr, i) {
        var n = i + 1;
        Array.prototype.forEach.call(
          tr.querySelectorAll("[aria-label]"),
          function (el) {
            var label = el.getAttribute("aria-label") || "";
            label = label.replace(
              /^(Pindahkan kriteria|Nama kriteria|Bobot kriteria|Hapus kriteria|Catatan prompt kriteria) \d+/,
              "$1 " + n
            );
            label = label.replace(
              /^Kriteria \d+ deskripsi skor/,
              "Kriteria " + n + " deskripsi skor"
            );
            el.setAttribute("aria-label", label);
          }
        );
      });
    }

    function updateRubric() {
      var rows = rowList();
      var total = 0;
      rows.forEach(function (tr) {
        var w = tr.querySelector('[data-f="weight"]');
        var v = w ? Number(w.value) || 0 : 0;
        total += v;
      });
      if (totalEl) {
        totalEl.textContent = "Total bobot: " + total + "%";
        totalEl.classList.toggle("is-bad", total !== 100);
      }
      if (submitBtn) submitBtn.disabled = rows.length === 0 || total !== 100;
      if (tableWrap) tableWrap.hidden = rows.length === 0;
      if (emptyEl) emptyEl.hidden = rows.length !== 0;
    }

    rubForm.addEventListener("submit", function () {
      serializeRubric();
    });
    rubForm.addEventListener("input", function (e) {
      if (e.target && e.target.closest && e.target.closest("[data-rubric-row]")) {
        updateRubric();
      }
    });

    var addBtn = rubForm.querySelector("[data-rubric-add]");
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        if (!tpl) return;
        body.appendChild(document.importNode(tpl.content, true));
        renumberRubric();
        updateRubric();
      });
    }

    body.addEventListener("click", function (e) {
      var rm =
        e.target && e.target.closest ? e.target.closest("[data-rubric-remove]") : null;
      if (!rm) return;
      var tr = rm.closest("[data-rubric-row]");
      if (tr) tr.parentNode.removeChild(tr);
      renumberRubric();
      updateRubric();
    });

    var dragTr = null;
    body.addEventListener("dragstart", function (e) {
      var tr = e.target && e.target.closest ? e.target.closest("[data-rubric-row]") : null;
      if (!tr) return;
      dragTr = tr;
      tr.classList.add("is-drag");
      try {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", "");
      } catch (err) {}
    });
    body.addEventListener("dragover", function (e) {
      if (!dragTr) return;
      e.preventDefault();
      var over = e.target && e.target.closest ? e.target.closest("[data-rubric-row]") : null;
      if (!over || over === dragTr) return;
      var rect = over.getBoundingClientRect();
      var after = e.clientY > rect.top + rect.height / 2;
      if (after) {
        if (over.nextSibling) body.insertBefore(dragTr, over.nextSibling);
        else body.appendChild(dragTr);
      } else {
        body.insertBefore(dragTr, over);
      }
    });
    function endDrag() {
      if (!dragTr) return;
      dragTr.classList.remove("is-drag");
      dragTr = null;
      renumberRubric();
      updateRubric();
    }
    body.addEventListener("dragend", endDrag);
    document.addEventListener("drop", endDrag);

    updateRubric();
  }

  var modeForm = document.querySelector("[data-mode-card]");
  if (modeForm) {
    var warn = modeForm.querySelector("[data-mode-warn]");
    var modeSubmit = modeForm.querySelector("[data-mode-submit]");
    var confirmBox = modeForm.querySelector("[name=confirm]");
    var blockers = modeForm.querySelectorAll("[data-blocker]");
    function syncMode() {
      var sel = modeForm.querySelector("[name=mode]:checked");
      var val = sel ? sel.value : "";
      if (warn) warn.hidden = val !== "langsung";
      if (modeSubmit) {
        modeSubmit.disabled =
          val === "langsung" &&
          (blockers.length > 0 || (confirmBox && !confirmBox.checked));
      }
    }
    modeForm.addEventListener("change", syncMode);
    syncMode();
  }
})();

// ---- Submissions inbox: course/status filters ----
(function () {
  var inbox = document.querySelector("[data-inbox]");
  if (!inbox) return;
  var courseSel = inbox.querySelector("[data-inbox-course]");
  var statusSel = inbox.querySelector("[data-inbox-status]");
  var countEl = inbox.querySelector("[data-inbox-count]");
  var tableWrap = inbox.querySelector("[data-inbox-table]");
  var emptyNone = inbox.querySelector("[data-inbox-empty-none]");
  var emptyFilter = inbox.querySelector("[data-inbox-empty-filter]");
  var rows = Array.prototype.slice.call(
    inbox.querySelectorAll("[data-inbox-row]")
  );
  var total = rows.length;

  function applyInbox() {
    var course = courseSel ? courseSel.value : "all";
    var status = statusSel ? statusSel.value : "all";
    var shown = 0;
    rows.forEach(function (tr) {
      var ok =
        (course === "all" || tr.getAttribute("data-course") === course) &&
        (status === "all" || tr.getAttribute("data-status") === status);
      tr.hidden = !ok;
      if (ok) shown++;
    });
    var hasFilter = course !== "all" || status !== "all";
    if (countEl) {
      countEl.textContent = shown + " dari " + total + " pengumpulan";
    }
    var none = shown === 0;
    if (tableWrap) tableWrap.hidden = none;
    if (emptyNone) emptyNone.hidden = !(none && !hasFilter);
    if (emptyFilter) emptyFilter.hidden = !(none && hasFilter);
  }
  if (courseSel) courseSel.addEventListener("change", applyInbox);
  if (statusSel) statusSel.addEventListener("change", applyInbox);
  applyInbox();
})();

// ---- Submission detail: grade editor (live nilai + hidden form submits) ----
(function () {
  var ed = document.querySelector("[data-grade-editor]");
  if (!ed) return;
  var rows = Array.prototype.slice.call(ed.querySelectorAll("[data-ge-row]"));
  var saveForm = ed.querySelector("[data-save-form]");
  var runForm = ed.querySelector("[data-run-form]");
  var liveEl = ed.querySelector("[data-ge-live]");
  var predEl = ed.querySelector("[data-ge-predikat]");

  function predikatOf(v) {
    if (v >= 85) return "A";
    if (v >= 70) return "B";
    if (v >= 55) return "C";
    return "D";
  }

  function updateLive() {
    var total = 0;
    rows.forEach(function (row) {
      var sel = row.querySelector("[data-ge-score]");
      var w = Number(row.getAttribute("data-weight")) || 0;
      total += (Number(sel ? sel.value : 1) / 4) * w;
    });
    var live = Math.round(total * 100) / 100;
    if (liveEl) liveEl.textContent = String(live);
    if (predEl) predEl.textContent = predikatOf(live);
  }

  function serialize() {
    return rows.map(function (row) {
      var sel = row.querySelector("[data-ge-score]");
      var quote = row.querySelector("[data-ge-quote]");
      var comment = row.querySelector("[data-ge-comment]");
      return {
        id: row.getAttribute("data-id"),
        score: Number(sel ? sel.value : 1),
        quote: quote ? quote.value : "",
        comment: comment ? comment.value : ""
      };
    });
  }

  function submitSave(intent) {
    if (!saveForm) return;
    var criteriaIn = saveForm.querySelector("[data-ge-criteria]");
    var feedbackIn = saveForm.querySelector("[data-ge-feedback-in]");
    var summaryIn = saveForm.querySelector("[data-ge-summary-in]");
    var intentIn = saveForm.querySelector("[data-ge-intent]");
    var feedback = ed.querySelector("[data-ge-feedback]");
    var summary = ed.querySelector("[data-ge-summary]");
    if (criteriaIn) criteriaIn.value = JSON.stringify(serialize());
    if (feedbackIn) feedbackIn.value = feedback ? feedback.value : "";
    if (summaryIn) summaryIn.value = summary ? summary.value : "";
    if (intentIn) intentIn.value = intent;
    saveForm.submit();
  }

  var saveBtns = Array.prototype.slice.call(
    ed.querySelectorAll("[data-save-btn]")
  );
  saveBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      submitSave(btn.getAttribute("data-intent") || "draft");
    });
  });

  var runBtn = ed.querySelector("[data-run-btn]");
  if (runBtn && runForm) {
    runBtn.addEventListener("click", function () {
      runForm.submit();
    });
  }

  rows.forEach(function (row) {
    row.addEventListener("change", updateLive);
    row.addEventListener("input", updateLive);
  });

  updateLive();
})();


/* ---- Student assignment: PG quiz (src/app/student/assignments/[id]/submit-form.tsx) ---- */
(function () {
  var quiz = document.querySelector("[data-sf-quiz]");
  if (!quiz) return;
  var total = parseInt(quiz.getAttribute("data-total"), 10) || 0;
  var hidden = document.querySelector("[data-sf-answers]");
  var submit = document.querySelector("[data-sf-submit]");
  var hint = document.querySelector("[data-sf-hint]");
  var counter = document.querySelector("[data-quiz-counter]");
  var dots = [].slice.call(quiz.querySelectorAll("[data-quiz-dot]"));
  var qs = [].slice.call(quiz.querySelectorAll("[data-quiz-q]"));
  var prev = quiz.querySelector("[data-quiz-prev]");
  var next = quiz.querySelector("[data-quiz-next]");
  var current = 0;

  function readAnswers() {
    var out = [];
    for (var i = 0; i < total; i++) {
      var checked = quiz.querySelector('input[name="choice_' + i + '"]:checked');
      out.push(checked ? checked.value : "");
    }
    return out;
  }

  function update() {
    var a = readAnswers();
    var unanswered = 0;
    for (var i = 0; i < a.length; i++) if (!a[i]) unanswered++;
    if (hidden) hidden.value = JSON.stringify(a);
    dots.forEach(function (d, i) {
      d.classList.toggle("is-answered", !!a[i]);
      if (i === current) {
        d.classList.add("is-current");
        d.setAttribute("aria-current", "true");
      } else {
        d.classList.remove("is-current");
        d.removeAttribute("aria-current");
      }
    });
    qs.forEach(function (q, i) {
      q.classList.toggle("is-hidden", i !== current);
    });
    if (counter) {
      counter.textContent =
        "Soal " + (current + 1) + " dari " + total +
        (unanswered > 0 ? " \u00b7 sisa " + unanswered + " soal belum dijawab" : "");
    }
    if (hint) {
      hint.textContent = unanswered > 0
        ? "Sisa " + unanswered + " soal belum dijawab."
        : "Setelah dikirim, jawaban terkunci dan tidak dapat diubah lagi.";
    }
    if (submit) submit.disabled = unanswered > 0;
    if (prev) prev.disabled = current === 0;
    if (next) next.disabled = current === total - 1;
  }

  dots.forEach(function (d, i) {
    d.addEventListener("click", function () {
      current = i;
      update();
    });
  });
  if (prev)
    prev.addEventListener("click", function () {
      current = Math.max(0, current - 1);
      update();
    });
  if (next)
    next.addEventListener("click", function () {
      current = Math.min(total - 1, current + 1);
      update();
    });
  quiz.addEventListener("change", function (e) {
    var t = e.target;
    if (t && t.name && t.name.indexOf("choice_") === 0) update();
  });

  var first = -1;
  var a0 = readAnswers();
  for (var j = 0; j < a0.length; j++) {
    if (!a0[j]) {
      first = j;
      break;
    }
  }
  current = first >= 0 ? first : 0;
  update();
})();
