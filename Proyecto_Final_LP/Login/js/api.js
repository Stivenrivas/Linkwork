async function api(method, path, body) {
  const opts = {
    method,
    headers: {},
    credentials: 'include'
  };
  if (body && !(body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (body instanceof FormData) {
    opts.body = body;
  }
  let res;
  try {
    res = await fetch('/api' + path + (path.includes('?') ? '&' : '?') + '_=' + Date.now(), opts);
  } catch (e) {
    throw new Error('No se puede conectar con el servidor. ¿Estará encendido?');
  }
  let data;
  try {
    data = await res.json();
  } catch (e) {
    throw new Error('El servidor respondió con datos inválidos (código ' + res.status + '). Recarga la página.');
  }
  if (!res.ok) throw new Error(data.error || 'Error ' + res.status);
  return data;
}

window.filtrarLista = function (boxId, rawQ) {
  const q = (rawQ || '').trim().toLowerCase();
  const box = document.getElementById(boxId);
  if (!box) return 0;
  let visible = 0;
  box.querySelectorAll('.listing-card').forEach(el => {
    const show = !q || el.textContent.toLowerCase().includes(q);
    el.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  const contador = document.getElementById(boxId + '_count');
  if (contador) contador.textContent = visible;
  return visible;
};

window.filtrarCards = function (boxId, rawQ) {
  return window.filtrarLista(boxId, rawQ);
};

window.filtrarCombo = function (boxId) {
  const box = document.getElementById(boxId);
  if (!box) return 0;
  const q = (document.getElementById(boxId + '_buscar') ? document.getElementById(boxId + '_buscar').value : '').trim().toLowerCase();
  const est = (document.getElementById(boxId + '_estado') ? document.getElementById(boxId + '_estado').value : '') || '';
  let visible = 0;
  box.querySelectorAll('.listing-card').forEach(el => {
    const txtOk = !q || el.textContent.toLowerCase().includes(q);
    const estOk = !est || (el.getAttribute('data-estado') || '') === est;
    const show = txtOk && estOk;
    el.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  const cont = document.getElementById(boxId + '_count');
  if (cont) cont.textContent = visible;
  return visible;
};

// --- Destacados / favoritos ---
let FAVS = new Set();
window.loadFavs = async function () {
  try { const l = await LW.favoritos(); FAVS = new Set(l.map(f => f.tipo + ':' + f.ref_id)); } catch (_) {}
};
window.esFav = function (tipo, id) { return FAVS.has(tipo + ':' + id); };
window.refrescarFavBtn = function (btn, tipo, id) {
  const on = esFav(tipo, id);
  btn.classList.toggle('fav-activo', on);
  btn.title = on ? 'Quitar de destacados' : 'Marcar como destacado';
  btn.innerHTML = on
    ? '<i class="material-icons" style="font-size:16px;">star</i>'
    : '<i class="material-icons" style="font-size:16px;">star_border</i>';
};
window.toggleFav = async function (btn, tipo, id) {
  try {
    const r = await LW.toggleFavorito(tipo, id);
    if (r.activo) FAVS.add(tipo + ':' + id); else FAVS.delete(tipo + ':' + id);
    refrescarFavBtn(btn, tipo, id);
  } catch (err) { swalErr(err); }
};
window.toggleFavorito = window.toggleFav;
window.toggleFiltroFav = function (chk, boxId) {
  const box = document.getElementById(boxId);
  if (!box) return;
  box.classList.toggle('fav-filter', chk.checked);
};

const LW = {
  // Auth
  me: () => api('GET', '/me'),
  login: (email, password) => api('POST', '/login', { email, password }),
  logout: () => api('POST', '/logout'),
  registro: (data) => api('POST', '/registro', data),
  updatePerfil: (data) => api('PATCH', '/perfil', data),
  cambiarPassword: (data) => api('POST', '/perfil/password', data),
  getCertificados: () => api('GET', '/certificados'),
  addCertificado: (data) => api('POST', '/certificados', data),
  deleteCertificado: (id) => api('DELETE', `/certificados/${id}`),
  getEmpresa: () => api('GET', '/perfil/empresa'),
  saveEmpresa: (data) => api('POST', '/perfil/empresa', data),

  // Usuarios (admin)
  getUsuarios: () => api('GET', '/usuarios'),
  deleteUsuario: (email) => api('DELETE', `/usuarios/${email}`),

  // Empleos
  getEmpleos: () => api('GET', '/empleos'),
  misEmpleos: () => api('POST', '/empleos/mis'),
  crearEmpleo: (data) => api('POST', '/empleos', data),
  editarEmpleo: (id, data) => api('PATCH', `/empleos/${id}`, data),
  deleteEmpleo: (id) => api('DELETE', `/empleos/${id}`),

  // Servicios
  getServicios: () => api('GET', '/servicios'),
  misServicios: () => api('POST', '/servicios/mis'),
  crearServicio: (data) => api('POST', '/servicios', data),
  editarServicio: (id, data) => api('PUT', `/servicios/${id}`, data),
  deleteServicio: (id) => api('DELETE', `/servicios/${id}`),

  // Upload
  upload: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api('POST', '/upload', fd);
  },

  // Aplicaciones
  aplicar: (tipo, ref_id, mensaje) => api('POST', '/aplicaciones', { tipo, ref_id, mensaje }),
  aplicacionesRecibidas: () => api('GET', '/aplicaciones/recibidas'),
  aplicacionesEnviadas: () => api('GET', '/aplicaciones/enviadas'),
  cambiarEstadoAplicacion: (id, estado) => api('PATCH', `/aplicaciones/${id}/estado`, { estado }),

  // Contratos
  crearContrato: (data) => api('POST', '/contratos', data),
  misContratos: () => api('GET', '/contratos/mis'),
  finalizarContrato: (id) => api('PATCH', `/contratos/${id}`, { estado: 'finalizado' }),
  setHorario: (id, data) => api('PATCH', `/contratos/${id}`, data),
  miEmpresa: () => api('GET', '/mi-empresa'),
  crearSolicitud: (data) => api('POST', '/solicitudes', data),
  misSolicitudes: () => api('GET', '/solicitudes'),
  solicitudesRecibidas: () => api('GET', '/solicitudes/recibidas'),
  responderSolicitud: (id, data) => api('PATCH', `/solicitudes/${id}/estado`, data),
  notificaciones: () => api('GET', '/notificaciones'),
  perfilPublico: (email) => api('GET', `/publico/${encodeURIComponent(email)}`),
  recibo: (id) => api('GET', `/recibo/${id}`),
  pregunta: () => api('GET', '/perfil/pregunta'),
  guardarPregunta: (data) => api('POST', '/perfil/pregunta', data),
  recuperarSolicitar: (email) => api('POST', '/recuperar/solicitar', { email }),
  recuperarCambiar: (data) => api('POST', '/recuperar/cambiar', data),
  misGrupos: () => api('GET', '/grupo/mis'),
  grupoMensajes: (id) => api('GET', `/grupo/${id}/mensajes`),
  enviarGrupo: (id, mensaje) => api('POST', `/grupo/${id}/mensajes`, { mensaje }),
  favoritos: () => api('GET', '/favoritos/mis'),
  toggleFavorito: (tipo, ref_id) => api('POST', '/favoritos', { tipo, ref_id }),

  // Finanzas
  crearFinanza: (data) => api('POST', '/finanzas', data),
  getFinanzas: (year, month) => {
    let q = '';
    if (year && month) q = `?year=${year}&month=${month}`;
    return api('GET', '/finanzas' + q);
  },
  resumenFinanzas: (year, month) => {
    let q = '';
    if (year && month) q = `?year=${year}&month=${month}`;
    return api('GET', '/finanzas/resumen' + q);
  },
  finanzasMensual: () => api('GET', '/finanzas/mensual'),

  // Mensajes
  enviarMensaje: (data) => api('POST', '/mensajes', data),
  getMensajes: (tipo_ref, ref_id) => api('GET', `/mensajes/${tipo_ref}/${ref_id}`),
  conversacion: (otroId, otroEmail, otroNombre) => {
    let q = '?';
    if (otroId) q += 'id=' + otroId + '&';
    q += 'email=' + encodeURIComponent(otroEmail || '') + '&nombre=' + encodeURIComponent(otroNombre || '');
    return api('GET', '/mensajes/conversacion' + q);
  },
  mensajesNoLeidos: () => api('GET', '/mensajes/no-leidos'),
  marcarLeido: (id) => api('PATCH', `/mensajes/leer/${id}`),
  conversaciones: () => api('GET', '/mensajes/conversaciones'),

  // Recomendaciones (usuario)
  recomendaciones: () => api('GET', '/recomendaciones'),

  // Frecuentes (proveedor)
  frecuentes: () => api('GET', '/frecuentes'),

  // Dashboard
  dashboardStats: () => api('GET', '/dashboard/stats'),
};

const SWAL_BASE = {
  background: '#FFFFFF',
  color: '#1E293B',
  confirmButtonColor: '#2563EB',
  cancelButtonColor: '#94A3B8',
  buttonsStyling: true,
  padding: '24px',
};

function swalErr(err) {
  Swal.fire({
    ...SWAL_BASE,
    icon: 'error',
    iconColor: '#EF4444',
    title: 'Error',
    text: err.message || err,
    confirmButtonText: 'Aceptar',
  });
}

function swalOk(msg) {
  Swal.fire({
    ...SWAL_BASE,
    icon: 'success',
    iconColor: '#10B981',
    title: msg,
    timer: 1800,
    showConfirmButton: false,
  });
}

function swalConfirm(title, text) {
  return Swal.fire({
    ...SWAL_BASE,
    icon: 'question',
    iconColor: '#F59E0B',
    title,
    text,
    showCancelButton: true,
    confirmButtonText: 'Sí',
    cancelButtonText: 'Cancelar',
    reverseButtons: true,
  });
}
