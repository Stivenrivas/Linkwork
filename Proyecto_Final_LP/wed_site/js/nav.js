window.addEventListener('pageshow', function (e) {
  if (e.persisted) window.location.reload();
});

(function autoLogoutOnBack() {
  const nav = performance.getEntriesByType('navigation')[0];
  if (!nav || nav.type !== 'back_forward') return;
  try { LW.logout(); } catch (_) {}
  history.replaceState(null, '', window.location.href);
  window.location.replace('../Login/index.html');
})();

document.addEventListener('DOMContentLoaded', async function () {
  let user;
  try {
    user = await LW.me();
  } catch (_) {
    window.location.replace('../Login/index.html');
    return;
  }

  const usernameEl = document.getElementById('navUsername');
  if (usernameEl) usernameEl.textContent = user.username;

  const roleText = { usuario: 'Usuario', proveedor: 'Proveedor', empleador: 'Empleador', admin: 'Administrador' };
  const ddName = document.getElementById('ddName');
  const ddEmail = document.getElementById('ddEmail');
  const ddRole = document.getElementById('ddRole');
  const ddAvatar = document.getElementById('ddAvatar');
  if (ddName) ddName.textContent = user.username;
  if (ddEmail) ddEmail.textContent = user.email;
  if (ddRole) ddRole.textContent = roleText[user.role] || user.role;
  if (ddAvatar && user.avatar) {
    ddAvatar.textContent = '';
    ddAvatar.style.backgroundImage = "url('" + user.avatar + "')";
    ddAvatar.style.backgroundSize = 'cover';
    ddAvatar.style.backgroundPosition = 'center';
  }

  async function logout() {
    try { await LW.logout(); } catch (_) {}
    history.replaceState(null, '', window.location.href);
    window.location.replace('../Login/index.html');
  }

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) logoutBtn.addEventListener('click', function (e) { e.preventDefault(); logout(); });

  const mobileLogout = document.getElementById('mobileLogout');
  if (mobileLogout) mobileLogout.addEventListener('click', function (e) { e.preventDefault(); logout(); });

  // ===== PERFIL =====
  const role = user.role;
  const withCerts = (role === 'usuario' || role === 'proveedor');
  const isProveedor = role === 'proveedor';
  const isEmpleador = role === 'empleador';
  injectProfileModal(role, (user.username || 'LW').charAt(0).toUpperCase());
  injectConfigModal();
  if (document.querySelector('[data-grupo-nav]')) injectGrupoModal();

  const ppTema = document.getElementById('ppTema');
  if (ppTema) {
    ppTema.value = curTema();
    ppTema.addEventListener('change', function () { setTema(this.value); });
  }

  const statusPregunta = document.getElementById('segPreguntaStatus');
  const ppPregunta = document.getElementById('ppPregunta');
  const ppRespuesta = document.getElementById('ppRespuesta');
  const ppSavePregunta = document.getElementById('ppSavePregunta');
  if (ppSavePregunta) {
    LW.pregunta().then(r => {
      if (r.tiene_pregunta) {
        ppPregunta.value = r.pregunta || '';
        statusPregunta.textContent = 'Tienes una pregunta configurada. Edítala y guarda para cambiarla.';
      }
    }).catch(() => {});
    ppSavePregunta.addEventListener('click', async function () {
      const pregunta = ppPregunta.value.trim();
      const respuesta = ppRespuesta.value.trim();
      if (!pregunta || !respuesta) { swalErr({ message: 'Completa la pregunta y la respuesta.' }); return; }
      try {
        await LW.guardarPregunta({ pregunta, respuesta });
        swalOk('Pregunta de seguridad guardada');
        ppRespuesta.value = '';
        statusPregunta.textContent = 'Tienes una pregunta configurada. Edítala y guarda para cambiarla.';
      } catch (err) { swalErr(err); }
    });
  }

  const ppDeleteAccount = document.getElementById('ppDeleteAccount');
  if (ppDeleteAccount) {
    ppDeleteAccount.addEventListener('click', async function () {
      const res = await Swal.fire({
        ...(typeof SWAL_BASE !== 'undefined' ? SWAL_BASE : {}),
        icon: 'warning',
        iconColor: '#EF4444',
        title: '¿Borrar tu cuenta?',
        text: 'Se eliminarán tu cuenta y todos tus datos. Esta acción no se puede deshacer.',
        showCancelButton: true,
        confirmButtonText: 'Sí, borrarla',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#DC2626',
        reverseButtons: true,
      });
      if (!res.isConfirmed) return;
      try {
        await LW.deleteUsuario(user.email);
        swalOk('Cuenta eliminada');
        setTimeout(function () { window.location.href = '../Login/index.html'; }, 1200);
      } catch (err) { swalErr(err); }
    });
  }

  let perfilAvatar = user.avatar || '';
  let cvUrl = user.cv_url || '';

  document.getElementById('ppEmail').value = user.email || '';
  document.getElementById('ppRole').value = roleText[role] || role;
  document.getElementById('ppUsername').value = user.username || '';
  document.getElementById('ppPhone').value = user.phone || '';
  if (user.avatar) {
    document.getElementById('ppAvatarImg').style.display = '';
    document.getElementById('ppAvatarImg').src = user.avatar;
  }

  const perfilItem = document.getElementById('perfilItem');
  if (perfilItem) {
    perfilItem.addEventListener('click', function (e) {
      e.preventDefault();
      const m = bootstrap.Modal.getOrCreateInstance(document.getElementById('profileModal'));
      m.show();
      loadProfileTabs();
    });
  }

  const configItem = document.getElementById('configItem');
  if (configItem) {
    configItem.addEventListener('click', function (e) {
      e.preventDefault();
      const m = bootstrap.Modal.getOrCreateInstance(document.getElementById('configModal'));
      m.show();
    });
  }

  document.getElementById('profileAvatarInput').addEventListener('change', async function (e) {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const up = await LW.upload(file);
      perfilAvatar = up.url;
      document.getElementById('ppAvatarImg').style = '';
      document.getElementById('ppAvatarImg').src = perfilAvatar;
    } catch (err) { swalErr(err); }
  });

  document.getElementById('ppSave').addEventListener('click', async function () {
    const username = document.getElementById('ppUsername').value.trim();
    const phone = document.getElementById('ppPhone').value.trim();
    if (!username) {
      Swal.fire({ icon: 'error', iconColor: '#EF4444', title: 'Error', text: 'El nombre es obligatorio', background: '#FFFFFF', color: '#1E293B', confirmButtonColor: '#2563EB', padding: '24px' });
      return;
    }
    const payload = {
      username, phone, avatar: perfilAvatar, cv_url: cvUrl,
      ciudad: val('ppCiudad'), experiencia: val('ppExperiencia'), sobre_mi: val('ppSobreMi')
    };
    if (role === 'usuario') {
      payload.profesion = val('ppProfesion');
      payload.habilidades = val('ppHabilidades');
    }
    if (isProveedor) {
      payload.especialidad = val('ppEspecialidad');
      payload.zona = val('ppZona');
      payload.portafolio = JSON.stringify(portafolio);
    }
    try {
      await LW.updatePerfil(payload);
      document.getElementById('navUsername').textContent = username;
      if (ddName) ddName.textContent = username;
      swalOk('Perfil actualizado');
    } catch (err) { swalErr(err); }
  });

  document.getElementById('ppChangePass').addEventListener('click', async function () {
    const current = document.getElementById('ppCurrent').value;
    const nuevo = document.getElementById('ppNew').value;
    const confirm = document.getElementById('ppConfirm').value;
    if (nuevo !== confirm) {
      Swal.fire({ icon: 'error', iconColor: '#EF4444', title: 'Error', text: 'Las contraseñas no coinciden', background: '#FFFFFF', color: '#1E293B', confirmButtonColor: '#2563EB', padding: '24px' });
      return;
    }
    try {
      await LW.cambiarPassword({ current, new: nuevo });
      document.getElementById('ppCurrent').value = '';
      document.getElementById('ppNew').value = '';
      document.getElementById('ppConfirm').value = '';
      swalOk('Contraseña actualizada');
    } catch (err) { swalErr(err); }
  });

  // Certificados
  if (withCerts) {
    document.getElementById('certAddBtn').addEventListener('click', async function () {
      const titulo = document.getElementById('certTitulo').value.trim();
      if (!titulo) { swalErr('El título es obligatorio'); return; }
      try {
        await LW.addCertificado({ titulo, institucion: val('certInst'), anio: val('certAnio'), url_imagen: certImagen });
        document.getElementById('certTitulo').value = '';
        document.getElementById('certInst').value = '';
        document.getElementById('certAnio').value = '';
        certImagen = '';
        document.getElementById('certPreview').style.display = 'none';
        swalOk('Certificado agregado');
        loadCertificados();
      } catch (err) { swalErr(err); }
    });
    document.getElementById('certImgInput').addEventListener('change', async function (e) {
      const file = e.target.files[0];
      if (!file) return;
      try { const up = await LW.upload(file); certImagen = up.url; const p = document.getElementById('certPreview'); p.src = up.url; p.style.display = ''; } catch (err) { swalErr(err); }
    });

    // CV
    document.getElementById('cvUploadBtn').addEventListener('click', function () { document.getElementById('cvFile').click(); });
    document.getElementById('cvFile').addEventListener('change', async function (e) {
      const file = e.target.files[0];
      if (!file) return;
      try { const up = await LW.upload(file); cvUrl = up.url; document.getElementById('cvStatus').textContent = 'Hoja de vida lista. Presiona "Guardar cambios".'; } catch (err) { swalErr(err); }
    });
  }

  // Portafolio (proveedor)
  if (isProveedor) {
    document.getElementById('portAddBtn').addEventListener('click', function () { document.getElementById('portImgInput').click(); });
    document.getElementById('portImgInput').addEventListener('change', async function (e) {
      const file = e.target.files[0];
      if (!file) return;
      try { const up = await LW.upload(file); portafolio.push(up.url); renderPortafolio(); } catch (err) { swalErr(err); }
    });
  }

  // Empresa
  if (isEmpleador) {
    document.getElementById('empLogoInput').addEventListener('change', async function (e) {
      const file = e.target.files[0];
      if (!file) return;
      try { const up = await LW.upload(file); empLogo = up.url; const p = document.getElementById('empLogoImg'); p.src = up.url; p.style.display = ''; } catch (err) { swalErr(err); }
    });
    document.getElementById('empSaveBtn').addEventListener('click', async function () {
      try {
        await LW.saveEmpresa({
          nombre: val('empNombre'), nit: val('empNit'), rubro: val('empRubro'),
          descripcion: val('empDesc'), tamano: val('empTamano'), sede: val('empSede'),
          logo: empLogo, web: val('empWeb')
        });
        swalOk('Empresa guardada');
      } catch (err) { swalErr(err); }
    });
  }

  async function loadProfileTabs() {
    if (withCerts) {
      loadCertificados();
      document.getElementById('cvStatus').textContent = cvUrl ? 'CV listo. Guarda si cambiaste algo.' : 'Aún no has subido tu hoja de vida.';
    }
    prefillProfesional();
    if (isProveedor) loadPortafolio();
    if (isEmpleador) loadEmpresa();
  }

  function prefillProfesional() {
    if (document.getElementById('ppCiudad')) document.getElementById('ppCiudad').value = user.ciudad || '';
    if (document.getElementById('ppProfesion')) document.getElementById('ppProfesion').value = user.profesion || '';
    if (document.getElementById('ppEspecialidad')) document.getElementById('ppEspecialidad').value = user.especialidad || '';
    if (document.getElementById('ppHabilidades')) document.getElementById('ppHabilidades').value = user.habilidades || '';
    if (document.getElementById('ppZona')) document.getElementById('ppZona').value = user.zona || '';
    if (document.getElementById('ppExperiencia')) document.getElementById('ppExperiencia').value = user.experiencia || '';
    if (document.getElementById('ppSobreMi')) document.getElementById('ppSobreMi').value = user.sobre_mi || '';
  }

  async function loadCertificados() {
    const list = document.getElementById('certList');
    list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Cargando...</p>';
    try {
      const certs = await LW.getCertificados();
      if (!certs.length) { list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Sin certificados.</p>'; return; }
      list.innerHTML = certs.map(c => {
        return '<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--card-border);">' +
          (c.url_imagen ? '<img src="' + c.url_imagen + '" style="width:44px;height:44px;object-fit:cover;border-radius:8px;">' : '<i class="material-icons" style="color:var(--accent);">workspace_premium</i>') +
          '<div style="flex:1;"><div style="font-weight:600;font-size:14px;">' + escHtml(c.titulo) + '</div>' +
          '<div style="font-size:12px;color:var(--text-muted);">' + escHtml(c.institucion || '') + (c.anio ? ' &middot; ' + escHtml(c.anio) : '') + '</div></div>' +
          '<button class="btn btn-sm btn-ghost" onclick="deleteCertificado(' + c.id + ')"><i class="material-icons" style="font-size:16px;color:var(--accent2);">delete</i></button>' +
        '</div>';
      }).join('');
    } catch (err) { list.innerHTML = '<p style="color:var(--accent2);font-size:13px;">' + escHtml(err.message) + '</p>'; }
  }

  function loadPortafolio() {
    try {
      if (user.portafolio) { const arr = JSON.parse(user.portafolio || '[]'); if (Array.isArray(arr)) portafolio = arr.filter(Boolean); else portafolio = []; }
      else portafolio = [];
    } catch (_) { portafolio = []; }
    renderPortafolio();
  }

  function renderPortafolio() {
    const c = document.getElementById('portList');
    if (!c) return;
    if (!portafolio.length) { c.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Sin trabajos. Agrega ejemplos de tu trabajo.</p>'; return; }
    c.innerHTML = portafolio.map((u, i) =>
      '<div style="position:relative;display:inline-block;margin:4px;">' +
        '<img src="' + u + '" style="width:70px;height:70px;object-fit:cover;border-radius:8px;border:1px solid var(--card-border);">' +
        '<button type="button" style="position:absolute;top:-6px;right:-6px;background:var(--accent2);color:#fff;border:none;border-radius:50%;width:20px;height:20px;font-size:12px;line-height:20px;cursor:pointer;" onclick="removePortafolio(' + i + ')">&times;</button>' +
      '</div>').join('');
  }

  async function loadEmpresa() {
    try {
      const e = await LW.getEmpresa();
      if (e && e.nombre !== undefined) {
        document.getElementById('empNombre').value = e.nombre || '';
        document.getElementById('empNit').value = e.nit || '';
        document.getElementById('empRubro').value = e.rubro || '';
        document.getElementById('empDesc').value = e.descripcion || '';
        document.getElementById('empTamano').value = e.tamano || '';
        document.getElementById('empSede').value = e.sede || '';
        document.getElementById('empWeb').value = e.web || '';
        if (e.logo) { empLogo = e.logo; document.getElementById('empLogoImg').style.display = ''; document.getElementById('empLogoImg').src = e.logo; }
      }
    } catch (_) {}
  }

  initNotificaciones(role);
});

function val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ''; }

// ===== Tema de la web =====
function curTema() { return localStorage.getItem('lw_tema') || 'claro'; }

function applyTema() {
  const t = curTema();
  let dark = t === 'oscuro';
  if (t === 'auto') dark = !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  if (dark) document.documentElement.setAttribute('data-theme', 'dark');
  else document.documentElement.removeAttribute('data-theme');
}

function setTema(t) {
  localStorage.setItem('lw_tema', t);
  applyTema();
  const sel = document.getElementById('ppTema');
  if (sel) sel.value = t;
}

applyTema();
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    if (curTema() === 'auto') applyTema();
  });
}

const __notifCleared = {};

function setNotifBadge(section, count) {
  if (!section) return;
  const targets = document.querySelectorAll('.dd-section-trigger[data-section="' + section + '"], [data-grupo-nav="' + section + '"]');
  targets.forEach(t => {
    let dot = t.querySelector('.notif-dot');
    if (count > 0) {
      if (!dot) {
        dot = document.createElement('span');
        dot.className = 'notif-dot';
        t.appendChild(dot);
      }
      dot.textContent = count > 9 ? '9+' : String(count);
      dot.style.display = 'inline-flex';
    } else if (dot) {
      dot.style.display = 'none';
    }
  });
}

async function pollNotificaciones(role) {
  let data;
  try { data = await LW.notificaciones(); } catch (_) { return; }
  if (!data) return;
  const map = { chat: 'chat', grupo: 'grupo' };
  if (role === 'empleador') { map.aplicaciones = 'solicitudes'; map.solicitudes = 'empresa'; }
  else if (role === 'usuario' || role === 'proveedor') { map.respuestas = 'empresa'; }
  for (const field in map) {
    const section = map[field];
    const count = data[field] || 0;
    const cleared = __notifCleared[section];
    setNotifBadge(section, (cleared !== undefined && count <= cleared) ? 0 : count);
  }
}

function initNotificaciones(role) {
  pollNotificaciones(role);
  setInterval(() => pollNotificaciones(role), 15000);
  document.addEventListener('click', function (e) {
    const t = e.target.closest('.dd-section-trigger, [data-grupo-nav]');
    if (!t) return;
    const section = t.dataset.section || t.dataset.grupoNav;
    const dot = t.querySelector('.notif-dot');
    const count = dot ? parseInt(dot.textContent, 10) : 0;
    __notifCleared[section] = count || 0;
    if (dot) dot.style.display = 'none';
  });
}

let certImagen = '';
let empLogo = '';
let portafolio = [];

async function deleteCertificado(id) {
  try { await LW.deleteCertificado(id); swalOk('Certificado eliminado'); loadCertificados(); } catch (err) { swalErr(err); }
}
function removePortafolio(i) {
  portafolio.splice(i, 1);
  renderPortafolio();
}
function switchProfileTab(tab) {
  document.querySelectorAll('.pp-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.pp-pane').forEach(p => p.style.display = 'none');
  const btn = document.querySelector('.pp-tab[data-tab="' + tab + '"]');
  if (btn) btn.classList.add('active');
  const pane = document.getElementById('pane-' + tab);
  if (pane) pane.style.display = 'block';
}

function injectProfileModal(role, avatarInitial) {
  const isEmpleador = role === 'empleador';
  const isProveedor = role === 'proveedor';
  const withCerts = (role === 'usuario' || role === 'proveedor');

  const profPane = withCerts ? `
    <div class="pp-pane" id="pane-profesional" style="display:none;">
      <div class="row g-2">
        <div class="col-6"><label class="form-label">Ciudad / Ubicación</label><input type="text" id="ppCiudad" class="form-control"></div>
        <div class="col-6"><label class="form-label">Años de experiencia</label><input type="text" id="ppExperiencia" class="form-control" placeholder="ej: 3 años"></div>
        ${role === 'usuario' ? '<div class="col-12"><label class="form-label">Área / Profesión</label><input type="text" id="ppProfesion" class="form-control" placeholder="ej: Administración, Diseño..."></div>' : ''}
        ${isProveedor ? '<div class="col-6"><label class="form-label">Especialidad</label><input type="text" id="ppEspecialidad" class="form-control" placeholder="ej: Plomería"></div><div class="col-6"><label class="form-label">Zona / Cobertura</label><input type="text" id="ppZona" class="form-control" placeholder="ej: Bogotá y alrededores"></div>' : ''}
        ${role === 'usuario' ? '<div class="col-12"><label class="form-label">Habilidades (separadas por coma)</label><input type="text" id="ppHabilidades" class="form-control" placeholder="ej: Excel, atención al cliente, trabajo en equipo"></div>' : ''}
        <div class="col-12"><label class="form-label">Sobre mí</label><textarea id="ppSobreMi" class="form-control" rows="3"></textarea></div>
      </div>
    </div>` : '';

  const portPane = isProveedor ? `
    <div class="pp-pane" id="pane-portafolio" style="display:none;">
      <h6 style="margin:0 0 8px;">Portafolio / Ejemplos de trabajos</h6>
      <button type="button" class="btn btn-ghost" id="portAddBtn"><i class="material-icons" style="font-size:16px;">add_photo_alternate</i> Agregar imagen</button>
      <input type="file" id="portImgInput" accept="image/*" style="display:none;">
      <div id="portList" style="margin-top:10px;"></div>
    </div>` : '';

  const certPane = withCerts ? `
    <div class="pp-pane" id="pane-certificados" style="display:none;">
      <h6 style="margin:0 0 12px;">Diplomas y certificados</h6>
      <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:12px;">
        <input type="text" id="certTitulo" class="form-control" placeholder="Título (ej. Técnico en Sistemas)">
        <input type="text" id="certInst" class="form-control" placeholder="Institución">
        <input type="text" id="certAnio" class="form-control" placeholder="Año (ej. 2025)">
        <div style="display:flex;gap:8px;align-items:center;">
          <button type="button" class="btn btn-ghost" onclick="document.getElementById('certImgInput').click();"><i class="material-icons" style="font-size:16px;">add_a_photo</i> Foto del diploma</button>
          <input type="file" id="certImgInput" accept="image/*" style="display:none;">
          <img id="certPreview" style="display:none;width:40px;height:40px;object-fit:cover;border-radius:6px;">
        </div>
        <button type="button" class="btn btn-primary" id="certAddBtn"><i class="material-icons">add</i> Agregar certificado</button>
      </div>
      <div id="certList"></div>
    </div>

    <div class="pp-pane" id="pane-cv" style="display:none;">
      <h6 style="margin:0 0 8px;">Hoja de vida</h6>
      <p style="color:var(--text-muted);font-size:13px;">Sube tu hoja de vida (PDF o imagen) para que los empleadores la vean.</p>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
        <button type="button" class="btn btn-ghost" id="cvUploadBtn"><i class="material-icons" style="font-size:16px;">upload_file</i> Subir CV</button>
        <input type="file" id="cvFile" accept=".pdf,image/*" style="display:none;">
        <span id="cvStatus" style="font-size:13px;color:var(--text-muted);"></span>
      </div>
    </div>` : '';

  const empPane = isEmpleador ? `
    <div class="pp-pane" id="pane-empresa" style="display:none;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="position:relative;width:64px;height:64px;">
          <img id="empLogoImg" style="display:none;width:64px;height:64px;border-radius:12px;object-fit:cover;">
          <div style="width:64px;height:64px;border-radius:12px;background:#EEF2FF;color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:22px;"><i class="material-icons">business</i></div>
        </div>
        <button type="button" class="btn btn-sm btn-ghost" onclick="document.getElementById('empLogoInput').click()"><i class="material-icons" style="font-size:16px;">add_photo_alternate</i> Logo</button>
        <input type="file" id="empLogoInput" accept="image/*" style="display:none;">
      </div>
      <div class="mb-2"><label class="form-label">Nombre de la empresa</label><input type="text" id="empNombre" class="form-control"></div>
      <div class="mb-2"><label class="form-label">NIT / RUT</label><input type="text" id="empNit" class="form-control"></div>
      <div class="row g-2 mb-2">
        <div class="col"><label class="form-label">Rubro</label><input type="text" id="empRubro" class="form-control"></div>
        <div class="col"><label class="form-label">Tamaño</label><input type="text" id="empTamano" class="form-control" placeholder="ej: 10 empleados"></div>
      </div>
      <div class="mb-2"><label class="form-label">Sede / Dirección</label><input type="text" id="empSede" class="form-control"></div>
      <div class="mb-2"><label class="form-label">Web / redes</label><input type="text" id="empWeb" class="form-control"></div>
      <div class="mb-2"><label class="form-label">Descripción de la empresa</label><textarea id="empDesc" class="form-control" rows="3"></textarea></div>
      <button type="button" class="btn btn-primary" id="empSaveBtn"><i class="material-icons">save</i> Guardar empresa</button>
    </div>` : '';

  const tabs = `
    <button class="btn btn-sm pp-tab active" data-tab="info" onclick="switchProfileTab('info')">Información</button>
    ${withCerts ? '<button class="btn btn-sm pp-tab" data-tab="profesional" onclick="switchProfileTab(\'profesional\')">Profesional</button>' : ''}
    ${withCerts ? '<button class="btn btn-sm pp-tab" data-tab="certificados" onclick="switchProfileTab(\'certificados\')">Certificados</button>' : ''}
    ${withCerts ? '<button class="btn btn-sm pp-tab" data-tab="cv" onclick="switchProfileTab(\'cv\')">Hoja de vida</button>' : ''}
    ${isProveedor ? '<button class="btn btn-sm pp-tab" data-tab="portafolio" onclick="switchProfileTab(\'portafolio\')">Portafolio</button>' : ''}
    ${isEmpleador ? '<button class="btn btn-sm pp-tab" data-tab="empresa" onclick="switchProfileTab(\'empresa\')">Mi Empresa</button>' : ''}`;

  const html = `
  <div class="modal fade" id="profileModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content" style="border:1px solid var(--card-border);border-radius:var(--radius);box-shadow:var(--shadow-lg);">
        <div class="modal-header" style="border-bottom:1px solid var(--card-border);">
          <h5 class="modal-title" style="font-weight:700;display:flex;align-items:center;gap:8px;"><i class="material-icons" style="color:var(--accent);">account_circle</i> Mi Perfil</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" style="padding:24px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
            <div style="position:relative;width:64px;height:64px;flex:0 0 64px;">
              <img id="ppAvatarImg" style="display:none;width:64px;height:64px;border-radius:50%;object-fit:cover;">
              <div id="ppAvatarPlaceholder" style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent-light));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:24px;">${avatarInitial}</div>
            </div>
            <button type="button" class="btn btn-sm btn-ghost" onclick="document.getElementById('profileAvatarInput').click();"><i class="material-icons" style="font-size:16px;">add_a_photo</i> Cambiar foto</button>
            <input type="file" id="profileAvatarInput" accept="image/*" style="display:none;">
          </div>

          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;border-bottom:1px solid var(--card-border);padding-bottom:8px;">${tabs}</div>

          <div class="pp-pane" id="pane-info">
            <div class="mb-3"><label class="form-label">Nombre de usuario</label><input type="text" id="ppUsername" class="form-control"></div>
            <div class="mb-3"><label class="form-label">Teléfono</label><input type="text" id="ppPhone" class="form-control"></div>
            <div class="mb-3"><label class="form-label">Correo (login)</label><input type="text" id="ppEmail" class="form-control" readonly></div>
            <div class="mb-3"><label class="form-label">Tipo de cuenta</label><input type="text" id="ppRole" class="form-control" readonly></div>
            <hr style="border-color:var(--card-border);">
            <h6 style="font-weight:700;margin:0 0 12px;">Cambiar contraseña</h6>
            <div class="mb-2"><label class="form-label">Contraseña actual</label><input type="password" id="ppCurrent" class="form-control" autocomplete="current-password"></div>
            <div class="mb-2"><label class="form-label">Nueva contraseña</label><input type="password" id="ppNew" class="form-control" minlength="6" autocomplete="new-password"></div>
            <div class="mb-2"><label class="form-label">Confirmar</label><input type="password" id="ppConfirm" class="form-control" autocomplete="new-password"></div>
            <button type="button" class="btn btn-ghost" id="ppChangePass" style="border:1px solid var(--card-border);"><i class="material-icons" style="font-size:16px;">check</i> Guardar contraseña</button>
          </div>

          ${profPane}
          ${certPane}
          ${portPane}
          ${empPane}
        </div>
        <div class="modal-footer" style="padding:12px 24px 16px;border-top:1px solid var(--card-border);">
          <button type="button" class="btn btn-ghost" data-bs-dismiss="modal" style="font-weight:600;color:var(--text-muted);">Cerrar</button>
          <button type="button" class="btn btn-primary" id="ppSave"><i class="material-icons">save</i> Guardar cambios</button>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}

// ===== CONFIGURACIÓN (modal independiente) =====
function injectConfigModal() {
  const html = `
  <div class="modal fade" id="configModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content" style="border:1px solid var(--card-border);border-radius:var(--radius);box-shadow:var(--shadow-lg);">
        <div class="modal-header" style="border-bottom:1px solid var(--card-border);">
          <h5 class="modal-title" style="font-weight:700;display:flex;align-items:center;gap:8px;"><i class="material-icons" style="color:var(--accent);">settings</i> Configuración</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" style="padding:24px;">
          <h6 style="font-weight:700;margin:0 0 4px;">Tema de la web</h6>
          <p style="color:var(--text-muted);font-size:13px;margin:0 0 12px;">Cómo se ve LinkWork en este navegador.</p>
          <div class="mb-2">
            <select id="ppTema" class="form-select">
              <option value="claro">Claro</option>
              <option value="oscuro">Oscuro</option>
              <option value="auto">Automático (según tu sistema)</option>
            </select>
          </div>
          <hr style="border-color:var(--card-border);">
          <h6 style="font-weight:700;margin:0 0 4px;">Pregunta de seguridad</h6>
          <p style="color:var(--text-muted);font-size:13px;margin:0 0 10px;" id="segPreguntaStatus">Para poder recuperar tu contraseña si la olvidas.</p>
          <div class="mb-2"><label class="form-label">Pregunta</label><input type="text" id="ppPregunta" class="form-control" maxlength="200" placeholder="ej: ¿Cuál es el nombre de tu mascota?"></div>
          <div class="mb-2"><label class="form-label">Respuesta</label><input type="text" id="ppRespuesta" class="form-control" maxlength="100" placeholder="Escribe la respuesta (no compartas con nadie)"></div>
          <button type="button" class="btn btn-ghost" id="ppSavePregunta" style="border:1px solid var(--card-border);"><i class="material-icons" style="font-size:16px;">shield</i> Guardar pregunta</button>
          <hr style="border-color:var(--card-border);">
          <h6 style="font-weight:700;margin:0 0 4px;color:#EF4444;">Eliminar cuenta</h6>
          <p style="color:var(--text-muted);font-size:13px;margin:0 0 10px;">Esta acción borra tu cuenta y todos tus datos. No se puede deshacer.</p>
          <button type="button" class="btn btn-outline-danger" id="ppDeleteAccount"><i class="material-icons" style="font-size:16px;">delete_forever</i> Borrar mi cuenta</button>
        </div>
        <div class="modal-footer" style="padding:12px 24px 16px;border-top:1px solid var(--card-border);">
          <button type="button" class="btn btn-ghost" data-bs-dismiss="modal" style="font-weight:600;color:var(--text-muted);">Cerrar</button>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}

function closeMobileNav() {
  const el = document.getElementById('mobile-nav');
  if (!el) return;
  const off = bootstrap.Offcanvas.getInstance(el);
  if (off) off.hide();
}

function swalOk(msg) {
  Swal.fire({ icon: 'success', iconColor: '#10B981', title: msg, timer: 1800, showConfirmButton: false, background: '#FFFFFF', color: '#1E293B', padding: '24px' });
}
function swalErr(err) {
  Swal.fire({ icon: 'error', iconColor: '#EF4444', title: 'Error', text: err && err.message ? err.message : String(err), background: '#FFFFFF', color: '#1E293B', padding: '24px' });
}
function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

async function openPerfilPublico(email) {
  let data;
  try {
    data = await LW.perfilPublico(email);
  } catch (err) { swalErr(err); return; }
  const u = data.usuario || {};
  const roleTxt = { usuario: 'Usuario', proveedor: 'Proveedor', empleador: 'Empleador' }[u.role] || u.role;
  const iniciales = (u.username || '?').substring(0, 2).toUpperCase();

  let certHtml = '<p style="color:var(--text-muted);font-size:13px;">Sin certificados.</p>';
  if (data.certificados && data.certificados.length) {
    certHtml = data.certificados.map(c =>
      '<div style="display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--card-border);">' +
        (c.url_imagen ? '<img src="' + escHtml(c.url_imagen) + '" style="width:44px;height:44px;object-fit:cover;border-radius:8px;">' : '<i class="material-icons" style="color:var(--accent);">workspace_premium</i>') +
        '<div><b style="font-size:14px;">' + escHtml(c.titulo) + '</b>' +
        (c.institucion || c.anio ? '<div style="font-size:12px;color:var(--text-muted);">' + escHtml(c.institucion || '') + (c.anio ? ' &middot; ' + escHtml(c.anio) : '') + '</div>' : '') +
        '</div></div>').join('');
  }

  let portHtml = '';
  if (u.portafolio) {
    let arr = [];
    try { arr = JSON.parse(u.portafolio || '[]'); } catch (_) { arr = []; }
    if (Array.isArray(arr) && arr.length) {
      portHtml = '<div>' + arr.map(p => '<img src="' + escHtml(p) + '" style="width:70px;height:70px;object-fit:cover;border-radius:8px;margin:4px;border:1px solid var(--card-border);">').join('') + '</div>';
    }
  }

  let empHtml = '';
  if (u.role === 'empleador' && data.empresa) {
    const e = data.empresa;
    empHtml = '<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--card-border);">' +
      (e.logo ? '<img src="' + escHtml(e.logo) + '" style="width:44px;height:44px;border-radius:8px;object-fit:cover;">' : '<i class="material-icons" style="color:var(--accent);">business</i>') +
      '<div><b>' + escHtml(e.nombre || 'Sin nombre') + '</b>' +
      '<div style="font-size:12px;color:var(--text-muted);">' + [e.rubro, e.sede, e.tamano].filter(Boolean).join(' &middot; ') + '</div>' +
      (e.descripcion ? '<div style="font-size:13px;margin-top:4px;">' + escHtml(e.descripcion) + '</div>' : '') +
      '</div></div>';
  }

  const rows = [];
  function add(label, val) { if (val) rows.push('<div class="pp-row"><span class="pp-label">' + label + '</span><span>' + escHtml(val) + '</span></div>'); }
  add('Ciudad', u.ciudad);
  add('Profesión', u.profesion);
  add('Especialidad', u.especialidad);
  add('Habilidades', u.habilidades);
  add('Experiencia', u.experiencia);
  add('Zona', u.zona);
  add('Sobre mí', u.sobre_mi);

  const html = `
  <div class="modal fade" id="publicProfileModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content" style="border:1px solid var(--card-border);border-radius:var(--radius);box-shadow:var(--shadow-lg);">
        <div class="modal-header" style="border-bottom:1px solid var(--card-border);">
          <h5 class="modal-title" style="font-weight:700;display:flex;align-items:center;gap:8px;"><i class="material-icons" style="color:var(--accent);">person</i> Perfil</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" style="padding:24px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
            ${u.avatar ? '<img src="' + escHtml(u.avatar) + '" style="width:64px;height:64px;border-radius:50%;object-fit:cover;">' : '<div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent-light));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:22px;">' + escHtml(iniciales) + '</div>'}
            <div>
              <h5 style="margin:0;font-weight:700;">${escHtml(u.username)}</h5>
              <div style="color:var(--text-muted);font-size:13px;">${escHtml(u.email)}${u.phone ? ' &middot; ' + escHtml(u.phone) : ''}</div>
              <span class="badge text-bg-primary" style="margin-top:4px;">${escHtml(roleTxt)}</span>
            </div>
          </div>

          ${u.cv_url ? '<div style="margin-bottom:12px;"><a href="' + escHtml(u.cv_url) + '" target="_blank" class="btn btn-ghost" style="border:1px solid var(--card-border);"><i class="material-icons" style="font-size:16px;">description</i> Ver hoja de vida</a></div>' : ''}

          ${rows.length ? '<div style="margin-bottom:16px;">' + rows.join('') + '</div>' : ''}

          ${u.role === 'empleador' ? '<h6 style="font-weight:700;margin-bottom:6px;">Empresa</h6>' + (empHtml || '<p style="color:var(--text-muted);font-size:13px;">Sin datos.</p>') : ''}

          <h6 style="font-weight:700;margin:14px 0 6px;">Certificados</h6>
          ${certHtml}

          ${portHtml ? '<h6 style="font-weight:700;margin:14px 0 6px;">Portafolio</h6>' + portHtml : ''}
        </div>
      </div>
    </div>
  </div>`;

  const old = document.getElementById('publicProfileModal');
  if (old) old.remove();
  document.body.insertAdjacentHTML('beforeend', html);
  bootstrap.Modal.getOrCreateInstance(document.getElementById('publicProfileModal')).show();
}

function fmtCOP(n) {
  return '$' + Number(n || 0).toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

// ===== Chat de equipo (grupos) =====
let __gruposChat = [];
let __grupoActualId = null;
let __grupoTimer = null;

function injectGrupoModal() {
  if (document.getElementById('grupoModal')) return;
  const html = `
  <div class="modal fade" id="grupoModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content" style="border:1px solid var(--card-border);border-radius:var(--radius);box-shadow:var(--shadow-lg);">
        <div class="modal-header" style="border-bottom:1px solid var(--card-border);">
          <h5 class="modal-title" style="font-weight:700;display:flex;align-items:center;gap:8px;"><i class="material-icons" style="color:var(--accent);">groups</i> <span id="grupoNombre">Chat de equipo</span></h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" style="padding:16px 24px;">
          <div id="grupoSelector" style="margin-bottom:12px;display:none;">
            <select id="grupoSelect" class="form-select"></select>
          </div>
          <div id="grupoMiembros" style="font-size:12px;color:var(--text-muted);margin-bottom:10px;"></div>
          <div id="grupoThread" style="height:360px;overflow-y:auto;background:#F1F5F9;border:1px solid var(--card-border);border-radius:var(--radius);padding:12px;"></div>
        </div>
        <div class="modal-footer" style="padding:12px 24px 16px;border-top:1px solid var(--card-border);">
          <div style="display:flex;flex:1;gap:8px;">
            <input type="text" id="grupoInput" class="form-control" placeholder="Escribe un mensaje al equipo..." maxlength="1000">
            <button type="button" class="btn btn-primary" id="grupoSendBtn" style="white-space:nowrap;"><i class="material-icons">send</i></button>
          </div>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  document.getElementById('grupoSendBtn').addEventListener('click', enviarGrupoMsg);
  document.getElementById('grupoInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') enviarGrupoMsg(); });
  document.getElementById('grupoSelect').addEventListener('change', function () {
    __grupoActualId = parseInt(this.value, 10);
    cargarGruposMsg();
  });
  document.getElementById('grupoModal').addEventListener('hidden.bs.modal', function () {
    if (__grupoTimer) { clearInterval(__grupoTimer); __grupoTimer = null; }
  });
}

function escHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function openGrupoChat(e) {
  if (e) e.preventDefault();
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('grupoModal'));
  modal.show();
  let grupos;
  try { grupos = await LW.misGrupos(); } catch (err) { swalErr(err); return; }
  __gruposChat = grupos;
  const thread = document.getElementById('grupoThread');
  if (!grupos.length) {
    document.getElementById('grupoNombre').textContent = 'Chat de equipo';
    document.getElementById('grupoSelector').style.display = 'none';
    document.getElementById('grupoMiembros').textContent = '';
    thread.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--text-muted);text-align:center;"><i class="material-icons" style="font-size:40px;">groups</i><p style="margin-top:10px;font-size:14px;">Aún no tienes un equipo.<br>Este canal aparece cuando hay un <b>contrato activo</b> con una empresa.</p></div>';
    __grupoActualId = null;
    return;
  }
  if (grupos.length > 1) {
    const sel = document.getElementById('grupoSelect');
    sel.innerHTML = grupos.map(g => '<option value="' + g.id + '">' + escHtml(g.nombre) + '</option>').join('');
    document.getElementById('grupoSelector').style.display = '';
  } else {
    document.getElementById('grupoSelector').style.display = 'none';
  }
  __grupoActualId = grupos[0].id;
  document.getElementById('grupoInput').disabled = false;
  await cargarGruposMsg();
  if (__grupoTimer) clearInterval(__grupoTimer);
  __grupoTimer = setInterval(cargarGruposMsg, 7000);
}

async function cargarGruposMsg() {
  const thread = document.getElementById('grupoThread');
  if (!__grupoActualId) return;
  let data;
  try { data = await LW.grupoMensajes(__grupoActualId); } catch (err) { return; }
  const g = data.grupo || {};
  document.getElementById('grupoNombre').textContent = (g.nombre || 'Chat de equipo');
  const miembros = data.miembros || [];
  document.getElementById('grupoMiembros').textContent = miembros.length
    ? 'Equipo: ' + miembros.map(m => m.nombre).join(', ')
    : '';
  if (!data.mensajes || !data.mensajes.length) {
    thread.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--text-muted);text-align:center;"><i class="material-icons" style="font-size:40px;">forum</i><p style="margin-top:10px;font-size:14px;">Sin mensajes todavía.<br>Empieza el canal de información de tu equipo.</p></div>';
    return;
  }
  thread.innerHTML = data.mensajes.map(m =>
    '<div style="display:flex;' + (m.es_mio ? 'justify-content:flex-end;' : 'justify-content:flex-start;') + 'margin-bottom:10px;">' +
      '<div class="' + (m.es_mio ? 'gso-mine' : 'gso-theirs') + '" style="max-width:78%;background:' + (m.es_mio ? 'var(--brand-gradient);color:#fff;' : '#fff;color:#1E293B;') + 'border:1px solid ' + (m.es_mio ? 'transparent' : 'var(--card-border)') + ';border-radius:14px 14px 14px 4px;padding:9px 12px;">' +
        '<div style="font-size:11px;font-weight:700;opacity:.85;margin-bottom:2px;">' + (m.es_mio ? 'Tú' : escHtml(m.user_nombre || '')) + '</div>' +
        '<div style="font-size:14px;line-height:1.4;word-break:break-word;white-space:pre-wrap;">' + escHtml(m.mensaje) + '</div>' +
        '<div style="font-size:10px;opacity:.75;margin-top:4px;">' + escHtml(String(m.created_at || '').slice(0, 16)) + '</div>' +
      '</div>' +
    '</div>').join('');
  thread.scrollTop = thread.scrollHeight;
}

async function enviarGrupoMsg() {
  const input = document.getElementById('grupoInput');
  const msg = input.value.trim();
  if (!msg || !__grupoActualId) return;
  input.value = '';
  try { await LW.enviarGrupo(__grupoActualId, msg); } catch (err) { swalErr(err); }
  await cargarGruposMsg();
}

async function openRecibo(id) {
  let r;
  try { r = await LW.recibo(id); } catch (err) { swalErr(err); return; }
  const emp = r.empresa || {};
  const em = r.empleado || {};
  const c = r.contrato || {};
  const dinero = (v) => fmtCOP(v);
  const fila = (l, v) => '<tr style="border-bottom:1px solid #e2e8f0;"><td style="padding:8px 10px;color:#334155;">' + l + '</td><td style="padding:8px 10px;text-align:right;color:#020617;font-weight:600;">' + v + '</td></tr>';
  let filasC = '';
  let tituloRec = 'RECIBO DE NÓMINA';
  if (r.por_hora) {
    tituloRec = 'RECIBO DE PAGO POR HORAS';
    filasC = fila('Pago por horas', dinero(r.base)) +
      fila('Total devengado', dinero(r.devengado)) +
      '<tr class="net"><td style="padding:10px;">NETO A PAGAR</td><td style="padding:10px;text-align:right;">' + dinero(r.neto) + '</td></tr>' +
      '<tr><td colspan="2" style="padding:10px;font-size:12px;color:#64748b;">Trabajo por hora: no se paga salario adicional, pensión ni auxilio de transporte.</td></tr>';
  } else {
    filasC = fila('Salario base', dinero(r.base)) +
      fila('Auxilio de transporte', dinero(r.auxilio)) +
      fila('Total devengado', dinero(r.devengado)) +
      fila('Salud (4%)', '-' + dinero(r.salud)) +
      fila('Pensión (4%)', '-' + dinero(r.pension)) +
      fila('Total deducciones', '-' + dinero(r.deducciones)) +
      '<tr class="net"><td style="padding:10px;">NETO A PAGAR</td><td style="padding:10px;text-align:right;">' + dinero(r.neto) + '</td></tr>';
  }
  const w = window.open('', '_blank', 'width=800,height=900');
  if (!w) { swalErr('Permite ventanas emergentes para ver el recibo'); return; }
  w.document.write('<html><head><title>Recibo</title><style>' +
    'body{font-family:Arial,Helvetica,sans-serif;color:#020617;margin:0;padding:32px;}' +
    '.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #2563eb;padding-bottom:14px;}' +
    'h1{margin:0;font-size:22px;color:#1d4ed8;} .dim{color:#64748b;font-size:13px;}' +
    'table{width:100%;border-collapse:collapse;margin:18px 0;} th{text-align:left;padding:8px 10px;background:#eff6ff;color:#1d4ed8;}' +
    '.total{font-size:17px;} .net{background:#ecfdf5;font-weight:700;}' +
    '.foot{margin-top:26px;font-size:12px;color:#64748b;border-top:1px solid #e2e8f0;padding-top:10px;}' +
    '@media print{body{print-color-adjust:exact;}}' +
    '</style></head><body>' +
    '<div class="header"><div><h1>' + tituloRec + '</h1><div class="dim">LinkWork &middot; Período: ' + escHtml(r.periodo || '') + '</div></div>' +
    '<div style="text-align:right;"><div style="font-weight:700;">' + escHtml(emp.nombre || '') + '</div>' +
    '<div class="dim">' + (emp.nit ? 'NIT ' + escHtml(emp.nit) : '') + (emp.sede ? '<br>' + escHtml(emp.sede) : '') + '</div></div></div>' +
    '<table><tr><th style="width:50%;">Empleado</th><th style="width:50%;">Contrato</th></tr>' +
    '<tr><td style="padding:8px 10px;"><b>' + escHtml(em.username || c.trabajador_nombre || '') + '</b><br><span class="dim">' + escHtml(em.email || c.trabajador_email || '') + (em.phone ? ' &middot; ' + escHtml(em.phone) : '') + '</span></td>' +
    '<td style="padding:8px 10px;"><b>' + escHtml(c.ref_titulo || '') + '</b><br><span class="dim">Días trabajados: ' + (r.dias_trabajados || 0) + '</span></td></tr></table>' +
    '<table>' +
      '<tr><th>Concepto</th><th style="text-align:right;">Valor</th></tr>' +
      filasC +
    '</table>' +
    '<div class="foot">Generado el ' + escHtml(r.fecha || '') + ' para ' + escHtml(em.username || c.trabajador_nombre || '') + '. Documento informativo, no reemplaza la seguridad social del trabajador.</div>' +
    '<script>window.onload=function(){setTimeout(function(){window.print();},300);};<\/script>' +
    '</body></html>');
  w.document.close();
}