function togglePW(id, btn) {
  const input = document.getElementById(id);
  const icon = btn.querySelector('i');
  input.type = input.type === 'password' ? 'text' : 'password';
  icon.textContent = input.type === 'password' ? 'visibility_off' : 'visibility';
}

// SWAL_BASE ya viene declarada en api.js (se carga antes que este archivo
// y ambos comparten el mismo scope global). No la vuelvas a declarar aquí:
// hacerlo con "const" duplicado rompe TODO este script con un SyntaxError,
// y por eso ningún listener de abajo llegaba a registrarse.

document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('loginPassword').value = '';

  // Toggle login / register
  function showLogin() {
    document.getElementById('loginCard').style.display = 'block';
    document.getElementById('registerCard').style.display = 'none';
    document.getElementById('showLoginBtn').classList.add('active');
    document.getElementById('showRegisterBtn').classList.remove('active');
  }

  function showRegister() {
    document.getElementById('loginCard').style.display = 'none';
    document.getElementById('registerCard').style.display = 'block';
    document.getElementById('showRegisterBtn').classList.add('active');
    document.getElementById('showLoginBtn').classList.remove('active');
  }

  document.getElementById('showLoginBtn').addEventListener('click', showLogin);
  document.getElementById('showRegisterBtn').addEventListener('click', showRegister);

  // Login
  document.getElementById('loginForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    document.getElementById('loginBtn').disabled = true;
    document.getElementById('loginBtn').innerHTML = '<i class="material-icons left">hourglass_empty</i>Ingresando...';
    try {
      const user = await LW.login(email, password);
      const routes = {
        usuario: '../wed_site/usuario.html',
        empleador: '../wed_site/empleador.html',
        proveedor: '../wed_site/provedor.html',
        admin: '../wed_site/dashboard.html',
      };
      window.location.href = routes[user.role] || '../wed_site/usuario.html';
    } catch (err) {
      Swal.fire({ ...SWAL_BASE, icon: 'error', iconColor: '#EF4444', title: 'Error al iniciar sesión', text: err.message, confirmButtonText: 'Aceptar' });
      document.getElementById('loginBtn').disabled = false;
      document.getElementById('loginBtn').innerHTML = 'Ingresar<i class="material-icons right">arrow_forward</i>';
    }
  });

  // Register
  document.getElementById('registerForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const data = {
      username: document.getElementById('regUsername').value.trim(),
      email: document.getElementById('regEmail').value.trim(),
      phone: document.getElementById('regPhone').value.trim(),
      password: document.getElementById('regPassword').value.trim(),
      role: document.getElementById('regRole').value,
    };
    document.getElementById('registerBtn').disabled = true;
    document.getElementById('registerBtn').innerHTML = '<i class="material-icons left">hourglass_empty</i>Creando...';
    try {
      await LW.registro(data);
      Swal.fire({ ...SWAL_BASE, icon: 'success', iconColor: '#10B981', title: 'Cuenta creada', text: 'Tu cuenta fue creada correctamente. Inicia sesión.', timer: 2500, showConfirmButton: false });
      document.getElementById('registerForm').reset();
      showLogin();
    } catch (err) {
      Swal.fire({ ...SWAL_BASE, icon: 'error', iconColor: '#EF4444', title: 'Error al registrarse', text: err.message, confirmButtonText: 'Aceptar' });
    }
    document.getElementById('registerBtn').disabled = false;
    document.getElementById('registerBtn').innerHTML = 'Crear Cuenta<i class="material-icons right">person_add</i>';
  });

  // Recuperar contraseña
  window.openRecoverModal = function () {
    document.getElementById('recoverEmail').value = '';
    document.getElementById('recoverStep1').style.display = 'block';
    document.getElementById('recoverStep2').style.display = 'none';
    document.getElementById('recoverContinue').style.display = '';
    document.getElementById('recoverSubmit').style.display = 'none';
    document.getElementById('recoverAnswer').value = '';
    document.getElementById('recoverEmailPassword').value = '';
    document.getElementById('recoverEmailPassword2').value = '';
    new bootstrap.Modal(document.getElementById('recoverModal')).show();
  };

  document.getElementById('recoverContinue').addEventListener('click', async function () {
    const email = document.getElementById('recoverEmail').value.trim();
    if (!email) {
      Swal.fire({ ...SWAL_BASE, icon: 'warning', iconColor: '#F59E0B', title: 'Ingresa tu correo', confirmButtonText: 'Aceptar' });
      return;
    }
    this.disabled = true;
    try {
      const r = await LW.recuperarSolicitar(email);
      if (!r.tiene_pregunta) {
        Swal.fire({ ...SWAL_BASE, icon: 'info', iconColor: '#3B82F6', title: 'No hay pregunta configurada', text: 'Ese correo no tiene una pregunta de seguridad. Usa tu contraseña habitual.', confirmButtonText: 'Aceptar' });
        return;
      }
      document.getElementById('recoverQuestion').textContent = r.pregunta;
      document.getElementById('recoverStep1').style.display = 'none';
      document.getElementById('recoverStep2').style.display = 'block';
      document.getElementById('recoverContinue').style.display = 'none';
      document.getElementById('recoverSubmit').style.display = '';
    } catch (err) {
      Swal.fire({ ...SWAL_BASE, icon: 'error', iconColor: '#EF4444', title: 'Error', text: err.message, confirmButtonText: 'Aceptar' });
    }
    document.getElementById('recoverContinue').disabled = false;
  });

  document.getElementById('recoverSubmit').addEventListener('click', async function () {
    const email = document.getElementById('recoverEmail').value.trim();
    const respuesta = document.getElementById('recoverAnswer').value.trim();
    const pw1 = document.getElementById('recoverEmailPassword').value;
    const pw2 = document.getElementById('recoverEmailPassword2').value;
    if (!respuesta) {
      Swal.fire({ ...SWAL_BASE, icon: 'warning', iconColor: '#F59E0B', title: 'Responde la pregunta', confirmButtonText: 'Aceptar' });
      return;
    }
    if (pw1.length < 6 || pw1 !== pw2) {
      Swal.fire({ ...SWAL_BASE, icon: 'warning', iconColor: '#F59E0B', title: 'Verifica la contraseña', text: 'Debe tener mínimo 6 caracteres y coincidir en ambos campos.', confirmButtonText: 'Aceptar' });
      return;
    }
    this.disabled = true;
    try {
      await LW.recuperarCambiar({ email, respuesta, nueva_password: pw1 });
      Swal.fire({ ...SWAL_BASE, icon: 'success', iconColor: '#10B981', title: 'Listo', text: 'Contraseña actualizada. Ya puedes iniciar sesión.', timer: 2500, showConfirmButton: false });
      bootstrap.Modal.getInstance(document.getElementById('recoverModal')).hide();
      document.getElementById('loginPassword').value = '';
    } catch (err) {
      Swal.fire({ ...SWAL_BASE, icon: 'error', iconColor: '#EF4444', title: 'Error', text: err.message, confirmButtonText: 'Aceptar' });
    }
    this.disabled = false;
  });
});