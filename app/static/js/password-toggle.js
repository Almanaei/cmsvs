/**
 * Password Toggle Functionality
 * Provides show/hide functionality for password fields across the application
 */

class PasswordToggle {
    constructor() {
        this.init();
    }

    init() {
        // Initialize all password fields on page load
        this.setupPasswordToggles();
        
        // Watch for dynamically added password fields
        this.observePasswordFields();
    }

    /**
     * Setup password toggles for all password fields on the page
     */
    setupPasswordToggles() {
        const passwordFields = document.querySelectorAll('input[type="password"]');
        
        passwordFields.forEach(field => {
            this.addToggleToPasswordField(field);
        });
    }

    /**
     * Add toggle functionality to a specific password field
     * @param {HTMLInputElement} passwordField - The password input field
     */
    addToggleToPasswordField(passwordField) {
        // Skip if toggle already exists
        if (passwordField.parentElement.querySelector('.password-toggle-btn')) {
            return;
        }

        // Ensure the parent has relative positioning
        const parent = passwordField.parentElement;
        if (!parent.classList.contains('relative')) {
            parent.classList.add('relative');
        }

        // Create toggle button
        const toggleBtn = this.createToggleButton(passwordField);
        
        // Insert toggle button
        parent.appendChild(toggleBtn);

        // Adjust padding to make room for the button
        this.adjustFieldPadding(passwordField);
    }

    /**
     * Create the toggle button element
     * @param {HTMLInputElement} passwordField - The password input field
     * @returns {HTMLButtonElement} The toggle button
     */
    createToggleButton(passwordField) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle-btn absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded p-1 transition-colors duration-200';
        button.setAttribute('aria-label', 'إظهار كلمة المرور');
        button.setAttribute('aria-pressed', 'false');
        button.setAttribute('tabindex', '0');

        // Create icon
        const icon = document.createElement('i');
        icon.className = 'fas fa-eye';
        icon.setAttribute('aria-hidden', 'true');
        button.appendChild(icon);

        // Add click event
        button.addEventListener('click', (e) => {
            e.preventDefault();
            this.togglePasswordVisibility(passwordField, button);
        });

        // Add keyboard support
        button.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.togglePasswordVisibility(passwordField, button);
            }
        });

        return button;
    }

    /**
     * Toggle password visibility
     * @param {HTMLInputElement} passwordField - The password input field
     * @param {HTMLButtonElement} toggleBtn - The toggle button
     */
    togglePasswordVisibility(passwordField, toggleBtn) {
        const isPassword = passwordField.type === 'password';
        const icon = toggleBtn.querySelector('i');

        // Toggle field type
        passwordField.type = isPassword ? 'text' : 'password';

        // Update icon
        icon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';

        // Update ARIA attributes
        toggleBtn.setAttribute('aria-label', isPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور');
        toggleBtn.setAttribute('aria-pressed', isPassword ? 'true' : 'false');

        // Add visual feedback
        toggleBtn.classList.add('text-blue-600');
        setTimeout(() => {
            toggleBtn.classList.remove('text-blue-600');
        }, 150);
    }

    /**
     * Adjust field padding to accommodate the toggle button
     * @param {HTMLInputElement} passwordField - The password input field
     */
    adjustFieldPadding(passwordField) {
        // Add left padding for the toggle button (RTL layout)
        const currentClasses = passwordField.className;
        
        // Remove any existing left padding classes
        passwordField.className = currentClasses.replace(/pl-\d+/g, '');
        
        // Add appropriate left padding
        if (!passwordField.className.includes('pl-')) {
            passwordField.classList.add('pl-10');
        }
    }

    /**
     * Observe for dynamically added password fields
     */
    observePasswordFields() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if the added node is a password field
                        if (node.type === 'password') {
                            this.addToggleToPasswordField(node);
                        }
                        
                        // Check for password fields within the added node
                        const passwordFields = node.querySelectorAll && node.querySelectorAll('input[type="password"]');
                        if (passwordFields) {
                            passwordFields.forEach(field => {
                                this.addToggleToPasswordField(field);
                            });
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Manually add toggle to specific password fields (for programmatic use)
     * @param {string|HTMLInputElement} selector - CSS selector or DOM element
     */
    static addToggle(selector) {
        const field = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (field && field.type === 'password') {
            const instance = new PasswordToggle();
            instance.addToggleToPasswordField(field);
        }
    }

    /**
     * Remove toggle from a password field
     * @param {string|HTMLInputElement} selector - CSS selector or DOM element
     */
    static removeToggle(selector) {
        const field = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (field) {
            const toggleBtn = field.parentElement.querySelector('.password-toggle-btn');
            if (toggleBtn) {
                toggleBtn.remove();
                // Reset field padding
                field.classList.remove('pl-10');
            }
        }
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PasswordToggle();
});

// Export for manual use
window.PasswordToggle = PasswordToggle;
