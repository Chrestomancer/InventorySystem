// Main JavaScript file for Inventory Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Date range picker initialization for reports
    if (document.getElementById('date-range-picker')) {
        flatpickr('#date-range-picker', {
            mode: 'range',
            dateFormat: 'Y-m-d'
        });
    }
    
    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Confirmation dialogs for delete actions
    document.querySelectorAll('.delete-confirm').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Dynamic form fields for inventory items
    const addFieldButton = document.getElementById('add-field-button');
    if (addFieldButton) {
        addFieldButton.addEventListener('click', function() {
            const container = document.getElementById('custom-fields-container');
            const fieldCount = container.children.length;
            
            const fieldGroup = document.createElement('div');
            fieldGroup.className = 'row mb-3';
            fieldGroup.innerHTML = `
                <div class="col-md-5">
                    <input type="text" class="form-control" name="custom_field_name_${fieldCount}" placeholder="Field Name">
                </div>
                <div class="col-md-5">
                    <input type="text" class="form-control" name="custom_field_value_${fieldCount}" placeholder="Field Value">
                </div>
                <div class="col-md-2">
                    <button type="button" class="btn btn-danger remove-field">Remove</button>
                </div>
            `;
            
            container.appendChild(fieldGroup);
            
            // Add event listener to the remove button
            fieldGroup.querySelector('.remove-field').addEventListener('click', function() {
                container.removeChild(fieldGroup);
            });
        });
    }
    
    // Calculate profit margin automatically in transaction form
    const calculateProfitMargin = function() {
        const finalSalePrice = parseFloat(document.getElementById('final_sale_price').value) || 0;
        const costPrice = parseFloat(document.getElementById('cost_price').value) || 0;
        const taxAmount = parseFloat(document.getElementById('tax_amount').value) || 0;
        const platformFee = parseFloat(document.getElementById('platform_fee').value) || 0;
        const shippingCost = parseFloat(document.getElementById('shipping_cost').value) || 0;
        const otherFees = parseFloat(document.getElementById('other_fees').value) || 0;
        
        const totalCost = costPrice + taxAmount + platformFee + shippingCost + otherFees;
        const profit = finalSalePrice - totalCost;
        const profitMargin = finalSalePrice > 0 ? (profit / finalSalePrice * 100) : 0;
        
        document.getElementById('profit').textContent = profit.toFixed(2);
        document.getElementById('profit_margin').textContent = profitMargin.toFixed(2) + '%';
        
        // Add color based on profit
        const profitElement = document.getElementById('profit');
        if (profit > 0) {
            profitElement.className = 'profit-positive';
        } else if (profit < 0) {
            profitElement.className = 'profit-negative';
        } else {
            profitElement.className = '';
        }
    };
    
    // Add event listeners to form fields for profit calculation
    const profitFields = ['final_sale_price', 'cost_price', 'tax_amount', 'platform_fee', 'shipping_cost', 'other_fees'];
    profitFields.forEach(function(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', calculateProfitMargin);
        }
    });
    
    // Initialize profit calculation if form exists
    if (document.getElementById('final_sale_price')) {
        calculateProfitMargin();
    }
    
    // Platform fee auto-calculation based on selected platform
    const platformSelect = document.getElementById('platform_id');
    if (platformSelect) {
        platformSelect.addEventListener('change', function() {
            const platformFeePercentage = this.options[this.selectedIndex].getAttribute('data-fee-percentage') || 0;
            const finalSalePrice = parseFloat(document.getElementById('final_sale_price').value) || 0;
            const platformFee = (finalSalePrice * platformFeePercentage / 100).toFixed(2);
            
            document.getElementById('platform_fee').value = platformFee;
            calculateProfitMargin();
        });
    }
});
