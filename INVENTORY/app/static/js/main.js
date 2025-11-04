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
    var dateRangePicker = document.getElementById('date-range-picker');
    if (dateRangePicker && typeof flatpickr === 'function') {
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
    const salePriceInput = document.getElementById('final_sale_price');
    const platformFeeInput = document.getElementById('platform_fee');
    const platformFeePercentageInput = document.getElementById('platform_fee_percentage');

    const readNumericInput = function(id) {
        const element = document.getElementById(id);
        if (!element) {
            return 0;
        }

        const value = parseFloat(element.value);
        return isNaN(value) ? 0 : value;
    };

    const calculateProfitMargin = function() {
        if (!salePriceInput) {
            return;
        }

        const finalSalePrice = readNumericInput('final_sale_price');
        const costPrice = readNumericInput('cost_price');
        const taxAmount = readNumericInput('tax_amount');
        const platformFee = readNumericInput('platform_fee');
        const shippingCost = readNumericInput('shipping_cost');
        const otherFees = readNumericInput('other_fees');

        const totalCost = costPrice + taxAmount + platformFee + shippingCost + otherFees;
        const profit = finalSalePrice - totalCost;
        const profitMargin = finalSalePrice > 0 ? (profit / finalSalePrice * 100) : 0;

        const profitElement = document.getElementById('profit');
        if (profitElement) {
            profitElement.textContent = '$' + profit.toFixed(2);
            profitElement.classList.remove('profit-positive', 'profit-negative');

            if (profit > 0) {
                profitElement.classList.add('profit-positive');
            } else if (profit < 0) {
                profitElement.classList.add('profit-negative');
            }
        }

        const marginElement = document.getElementById('profit_margin');
        if (marginElement) {
            marginElement.textContent = profitMargin.toFixed(2) + '%';
        }
    };

    const getPlatformFeePercentage = function() {
        if (platformFeePercentageInput) {
            const percentage = parseFloat(platformFeePercentageInput.value);
            return isNaN(percentage) ? 0 : percentage;
        }

        if (salePriceInput) {
            const fromDataset = salePriceInput.getAttribute('data-fee-percentage');
            if (fromDataset) {
                const parsed = parseFloat(fromDataset);
                return isNaN(parsed) ? 0 : parsed;
            }
        }

        return 0;
    };

    const updatePlatformFeeFromSalePrice = function() {
        if (!salePriceInput) {
            return;
        }

        const salePriceValue = parseFloat(salePriceInput.value);
        const platformFeePercentage = getPlatformFeePercentage();

        if (platformFeeInput && !isNaN(salePriceValue)) {
            const feeAmount = salePriceValue * platformFeePercentage / 100;
            platformFeeInput.value = feeAmount.toFixed(2);
        }

        calculateProfitMargin();
    };

    // Add event listeners to form fields for profit calculation
    const profitFields = ['tax_amount', 'platform_fee', 'shipping_cost', 'other_fees'];
    profitFields.forEach(function(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', calculateProfitMargin);
        }
    });

    if (salePriceInput) {
        salePriceInput.addEventListener('input', updatePlatformFeeFromSalePrice);
        salePriceInput.addEventListener('change', updatePlatformFeeFromSalePrice);

        const autoCalcFlag = salePriceInput.getAttribute('data-auto-calc');
        const shouldAutoCalculateOnLoad = (autoCalcFlag && autoCalcFlag.toLowerCase() === 'true') ||
            (platformFeeInput && platformFeeInput.value.trim() === '');

        if (shouldAutoCalculateOnLoad) {
            updatePlatformFeeFromSalePrice();
        }
    }
});
