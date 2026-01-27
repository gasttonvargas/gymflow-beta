/**
 * GymFlow - Interactividad del Frontend
 * Funciones para formularios dinámicos y UX mejorada
 */

// ===== GESTIÓN DE EJERCICIOS EN FORMULARIO DE RUTINA =====
let ejercicioCount = 0;

function agregarEjercicio() {
  const container = document.getElementById('ejercicios-container');
  
  const ejercicioHTML = `
    <div class="ejercicio-form-item" id="ejercicio-${ejercicioCount}">
      <div class="ejercicio-form-header">
        <span class="ejercicio-form-title">Ejercicio ${ejercicioCount + 1}</span>
        <button type="button" class="btn btn-danger btn-sm" onclick="eliminarEjercicio(${ejercicioCount})">
          Eliminar
        </button>
      </div>
      
      <div class="form-group">
        <label class="form-label">Nombre del ejercicio</label>
        <input type="text" name="ejercicio_nombre_${ejercicioCount}" class="form-input" 
               placeholder="Ej: Sentadillas" required>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Series</label>
          <input type="number" name="ejercicio_series_${ejercicioCount}" class="form-input" 
                 placeholder="3" min="1" required>
        </div>
        
        <div class="form-group">
          <label class="form-label">Repeticiones</label>
          <input type="text" name="ejercicio_reps_${ejercicioCount}" class="form-input" 
                 placeholder="12" required>
        </div>
        
        <div class="form-group">
          <label class="form-label">Descanso</label>
          <input type="text" name="ejercicio_descanso_${ejercicioCount}" class="form-input" 
                 placeholder="60 seg" required>
        </div>
      </div>
      
      <div class="form-group">
        <label class="form-label">Notas (opcional)</label>
        <textarea name="ejercicio_notas_${ejercicioCount}" class="form-textarea" rows="2"
                  placeholder="Indicaciones específicas..."></textarea>
      </div>
    </div>
  `;
  
  container.insertAdjacentHTML('beforeend', ejercicioHTML);
  ejercicioCount++;
}

function eliminarEjercicio(id) {
  const elemento = document.getElementById(`ejercicio-${id}`);
  if (elemento) {
    elemento.remove();
  }
}

// Inicializar con un ejercicio por defecto al cargar la página
document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('ejercicios-container');
  if (container && container.children.length === 0) {
    agregarEjercicio();
  }
});

// ===== CONFIRMACIÓN DE ELIMINACIÓN =====
function confirmarEliminacion(mensaje) {
  return confirm(mensaje || '¿Estás seguro de que querés eliminar esto?');
}

// ===== AUTO-CERRAR MENSAJES FLASH =====
document.addEventListener('DOMContentLoaded', function() {
  const flashMessages = document.querySelectorAll('.flash');
  
  flashMessages.forEach(function(flash) {
    setTimeout(function() {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity 0.5s ease';
      
      setTimeout(function() {
        flash.remove();
      }, 500);
    }, 5000); // Se cierra después de 5 segundos
  });
});

// ===== CALCULAR FECHA DE VENCIMIENTO AUTOMÁTICA =====
function calcularVencimiento(meses) {
  const fechaInicio = document.getElementById('fecha_inicio');
  const fechaVencimiento = document.getElementById('fecha_vencimiento');
  
  if (fechaInicio && fechaInicio.value) {
    const inicio = new Date(fechaInicio.value);
    inicio.setMonth(inicio.getMonth() + meses);
    
    const year = inicio.getFullYear();
    const month = String(inicio.getMonth() + 1).padStart(2, '0');
    const day = String(inicio.getDate()).padStart(2, '0');
    
    fechaVencimiento.value = `${year}-${month}-${day}`;
  }
}

// ===== VALIDACIÓN DE FORMULARIOS =====
function validarFormularioAlumno() {
  const nombre = document.querySelector('input[name="nombre"]').value.trim();
  const telefono = document.querySelector('input[name="telefono"]').value.trim();
  
  if (!nombre) {
    alert('Por favor, ingresá el nombre del alumno');
    return false;
  }
  
  if (!telefono) {
    alert('Por favor, ingresá el teléfono del alumno');
    return false;
  }
  
  return true;
}

// ===== BÚSQUEDA EN TIEMPO REAL =====
function filtrarAlumnos() {
  const input = document.getElementById('search-input');
  const filtro = input.value.toLowerCase();
  const alumnos = document.querySelectorAll('.alumno-item');
  
  alumnos.forEach(function(alumno) {
    const nombre = alumno.querySelector('.alumno-nombre').textContent.toLowerCase();
    
    if (nombre.includes(filtro)) {
      alumno.style.display = '';
    } else {
      alumno.style.display = 'none';
    }
  });
}