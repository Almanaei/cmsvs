/**
 * CMSVS Admin Forms JavaScript
 * Clean, accessible form validation and interaction
 */

class AdminFormValidator {
    constructor(formId) {
        this.form = document.getElementById(formId);
        this.errors = new Map();
        this.init();
    }

    init() {
        if (!this.form) {
            console.error('Form not found:', this.formId);
            return;
        }

        this.setupEventListeners();
        this.setupPasswordToggle();
        this.setupRealTimeValidation();
    }

    setupEventListeners() {
        // Form submission validation
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                this.showFirstError();
            }
        });

        // Password confirmation validation
        const confirmPassword = this.form.querySelector('#confirm_password');
        if (confirmPassword) {
            confirmPassword.addEventListener('input', () => {
                this.validatePasswordMatch();
            });
        }
    }

    setupPasswordToggle() {
        const toggleBtn = this.form.querySelector('#togglePassword');
        const passwordField = this.form.querySelector('#password');

        if (toggleBtn && passwordField) {
            toggleBtn.addEventListener('click', () => {
                const isPassword = passwordField.type === 'password';
                passwordField.type = isPassword ? 'text' : 'password';
                
                const icon = toggleBtn.querySelector('i');
                icon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
                
                // Update ARIA label for accessibility
                toggleBtn.setAttribute('aria-label', 
                    isPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'
                );
            });
        }
    }

    setupRealTimeValidation() {
        // Username validation
        const usernameField = this.form.querySelector('#username');
        if (usernameField) {
            usernameField.addEventListener('input', () => {
                this.validateUsername();
            });
        }

        // Email validation
        const emailField = this.form.querySelector('#email');
        if (emailField) {
            emailField.addEventListener('blur', () => {
                this.validateEmail();
            });
        }

        // Password validation
        const passwordField = this.form.querySelector('#password');
        if (passwordField) {
            passwordField.addEventListener('input', () => {
                this.validatePassword();
                this.validatePasswordMatch(); // Also check match when password changes
            });
        }
    }

    validateForm() {
        this.clearAllErrors();
        let isValid = true;

        // Validate required fields
        const requiredFields = this.form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.setFieldError(field, 'هذا الحقل مطلوب');
                isValid = false;
            }
        });

        // Specific validations
        if (!this.validateUsername()) isValid = false;
        if (!this.validateEmail()) isValid = false;
        if (!this.validatePassword()) isValid = false;
        if (!this.validatePasswordMatch()) isValid = false;
        if (!this.validateRole()) isValid = false;

        return isValid;
    }

    validateUsername() {
        const field = this.form.querySelector('#username');
        if (!field) return true;

        const username = field.value.trim();
        const pattern = /^[a-zA-Z0-9_]{3,20}$/;

        if (username && !pattern.test(username)) {
            this.setFieldError(field, 'اسم المستخدم يجب أن يكون بين 3-20 حرف ويحتوي على أحرف وأرقام وشرطة سفلية فقط');
            return false;
        }

        this.clearFieldError(field);
        return true;
    }

    validateEmail() {
        const field = this.form.querySelector('#email');
        if (!field) return true;

        const email = field.value.trim();
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (email && !pattern.test(email)) {
            this.setFieldError(field, 'يرجى إدخال بريد إلكتروني صحيح');
            return false;
        }

        this.clearFieldError(field);
        return true;
    }

    validatePassword() {
        const field = this.form.querySelector('#password');
        if (!field) return true;

        const password = field.value;

        if (password && password.length < 6) {
            this.setFieldError(field, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل');
            return false;
        }

        this.clearFieldError(field);
        return true;
    }

    validatePasswordMatch() {
        const passwordField = this.form.querySelector('#password');
        const confirmField = this.form.querySelector('#confirm_password');
        
        if (!passwordField || !confirmField) return true;

        const password = passwordField.value;
        const confirmPassword = confirmField.value;

        if (confirmPassword && password !== confirmPassword) {
            this.setFieldError(confirmField, 'كلمات المرور غير متطابقة');
            return false;
        }

        this.clearFieldError(confirmField);
        return true;
    }

    validateRole() {
        const field = this.form.querySelector('#role');
        if (!field) return true;

        if (!field.value) {
            this.setFieldError(field, 'يرجى اختيار دور المستخدم');
            return false;
        }

        this.clearFieldError(field);
        return true;
    }

    setFieldError(field, message) {
        this.clearFieldError(field);
        
        // Add error styling
        field.classList.add('border-red-300');
        field.classList.remove('border-gray-300');
        field.setAttribute('aria-invalid', 'true');

        // Create error message element
        const errorElement = document.createElement('div');
        errorElement.className = 'admin-form-error';
        errorElement.textContent = message;
        errorElement.id = `${field.id}-error`;
        
        // Associate error with field for accessibility
        field.setAttribute('aria-describedby', errorElement.id);

        // Insert error message after the field
        field.parentNode.appendChild(errorElement);
        
        this.errors.set(field.id, message);
    }

    clearFieldError(field) {
        // Remove error styling
        field.classList.remove('border-red-300');
        field.classList.add('border-gray-300');
        field.removeAttribute('aria-invalid');
        field.removeAttribute('aria-describedby');

        // Remove error message
        const errorElement = field.parentNode.querySelector('.admin-form-error');
        if (errorElement) {
            errorElement.remove();
        }

        this.errors.delete(field.id);
    }

    clearAllErrors() {
        const errorElements = this.form.querySelectorAll('.admin-form-error');
        errorElements.forEach(element => element.remove());

        const fields = this.form.querySelectorAll('.border-red-300');
        fields.forEach(field => {
            field.classList.remove('border-red-300');
            field.classList.add('border-gray-300');
            field.removeAttribute('aria-invalid');
            field.removeAttribute('aria-describedby');
        });

        this.errors.clear();
    }

    showFirstError() {
        const firstErrorField = this.form.querySelector('.border-red-300');
        if (firstErrorField) {
            firstErrorField.focus();
            firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    showAlert(message, type = 'error') {
        // Create a simple, accessible alert
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} mb-4`;
        alert.setAttribute('role', 'alert');
        alert.textContent = message;

        // Insert at the top of the form
        this.form.insertBefore(alert, this.form.firstChild);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize form validation when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize new user form validation
    const newUserForm = document.getElementById('newUserForm');
    if (newUserForm) {
        new AdminFormValidator('newUserForm');
    }

    // Add any other form initializations here
});

// Export for potential use in other scripts
window.AdminFormValidator = AdminFormValidator;
