document.addEventListener("DOMContentLoaded", () => {
    // --- Constants and State ---
    const API_BASE_URL = "/api";
    const ADMIN_API_BASE_URL = "/admin/api";
    const brasiliaTz = "America/Sao_Paulo"; // For displaying times

    // --- DOM Elements ---
    const clientView = document.getElementById("client-view");
    const adminView = document.getElementById("admin-view");
    const showClientBtn = document.getElementById("show-client-view");
    const showAdminBtn = document.getElementById("show-admin-view");

    // Client View Elements
    const serviceSelect = document.getElementById("service-select");
    const dateSelect = document.getElementById("date-select");
    const slotsContainer = document.getElementById("available-slots-container");
    const bookingForm = document.getElementById("booking-form");
    const confirmService = document.getElementById("confirm-service");
    const confirmDatetime = document.getElementById("confirm-datetime");
    const clientNameInput = document.getElementById("client-name");
    const clientPhoneInput = document.getElementById("client-phone");
    const cancelBookingBtn = document.getElementById("cancel-booking");
    const bookingResultDiv = document.getElementById("booking-result");

    // Admin View Elements
    const serviceForm = document.getElementById("service-form");
    const serviceIdInput = document.getElementById("service-id");
    const serviceNameInput = document.getElementById("service-name");
    const serviceDurationInput = document.getElementById("service-duration");
    const servicePriceInput = document.getElementById("service-price");
    const saveServiceBtn = document.getElementById("save-service-btn");
    const clearServiceFormBtn = document.getElementById("clear-service-form-btn");
    const serviceListUl = document.getElementById("service-list");
    const serviceAdminResultDiv = document.getElementById("service-admin-result");
    const refreshAppointmentsBtn = document.getElementById("refresh-appointments-btn");
    const appointmentListUl = document.getElementById("appointment-list");
    const appointmentAdminResultDiv = document.getElementById("appointment-admin-result");

    // --- Utility Functions ---
    const displayMessage = (element, message, isSuccess) => {
        element.textContent = message;
        element.className = isSuccess ? "success" : "error";
        element.style.display = "block";
        setTimeout(() => { element.style.display = "none"; }, 5000); // Hide after 5 seconds
    };

    const formatDate = (dateString) => {
        // Basic date formatting, consider a library for complex needs
        const options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: brasiliaTz }; 
        try {
             const date = new Date(dateString);
             // Check if date is valid before formatting
             if (isNaN(date.getTime())) {
                 return "Data inválida";
             }
             return date.toLocaleString("pt-BR", options);
        } catch (e) {
            console.error("Error formatting date:", dateString, e);
            return dateString; // Return original string if formatting fails
        }
    };
    
    // Set min date for date picker to today (considering Brasilia time)
    const setMinDate = () => {
        const today = new Date();
        // Adjust to Brasilia timezone for comparison if needed, but for date input, YYYY-MM-DD is usually sufficient
        // For simplicity, we'll use the local machine's date which is generally fine for 'min'
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
        const dd = String(today.getDate()).padStart(2, '0');
        dateSelect.min = `${yyyy}-${mm}-${dd}`;
    };

    // --- API Call Functions ---
    const fetchServices = async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("Error fetching services:", error);
            displayMessage(bookingResultDiv, "Erro ao carregar serviços.", false);
            displayMessage(serviceAdminResultDiv, "Erro ao carregar serviços.", false);
            return [];
        }
    };

    const fetchAvailableSlots = async (serviceId, date) => {
        if (!serviceId || !date) return;
        slotsContainer.innerHTML = "<p>Carregando horários...</p>";
        bookingForm.style.display = "none"; // Hide form while loading
        try {
            const response = await fetch(`${API_BASE_URL}/available_slots?service_id=${serviceId}&date=${date}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            renderAvailableSlots(data.available_slots || []);
        } catch (error) {
            console.error("Error fetching slots:", error);
            slotsContainer.innerHTML = "<p class='error'>Erro ao buscar horários disponíveis.</p>";
        }
    };

    const submitBooking = async (bookingData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/appointments`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(bookingData),
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            displayMessage(bookingResultDiv, `Agendamento confirmado para ${result.client_name} (${result.service_name}) em ${formatDate(result.appointment_time)}!`, true);
            bookingForm.style.display = "none";
            bookingForm.reset();
            slotsContainer.innerHTML = "<p>Selecione um serviço e uma data para ver os horários.</p>"; // Reset slots
            dateSelect.value = ''; // Clear date selection
            serviceSelect.selectedIndex = 0; // Reset service selection
        } catch (error) {
            console.error("Error submitting booking:", error);
            displayMessage(bookingResultDiv, `Erro ao agendar: ${error.message}`, false);
        }
    };

    const saveService = async (serviceData, method, url) => {
         try {
            const response = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(serviceData),
            });
            const result = await response.json();
             if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            displayMessage(serviceAdminResultDiv, result.message, true);
            clearServiceForm();
            loadAdminServices(); // Refresh list
        } catch (error) {
            console.error("Error saving service:", error);
            displayMessage(serviceAdminResultDiv, `Erro ao salvar serviço: ${error.message}`, false);
        }
    };
    
    const deleteService = async (serviceId) => {
        if (!confirm(`Tem certeza que deseja excluir o serviço ID ${serviceId}?`)) return;
        try {
            const response = await fetch(`${ADMIN_API_BASE_URL}/services/${serviceId}`, { method: "DELETE" });
            const result = await response.json();
             if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            displayMessage(serviceAdminResultDiv, result.message, true);
            loadAdminServices(); // Refresh list
        } catch (error) {
            console.error("Error deleting service:", error);
            displayMessage(serviceAdminResultDiv, `Erro ao excluir serviço: ${error.message}`, false);
        }
    };

    const fetchAppointments = async () => {
        appointmentListUl.innerHTML = "<li>Carregando agendamentos...</li>";
        try {
            const response = await fetch(`${ADMIN_API_BASE_URL}/appointments`);
             if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const appointments = await response.json();
            renderAppointments(appointments);
             displayMessage(appointmentAdminResultDiv, "Lista de agendamentos atualizada.", true);
        } catch (error) {
            console.error("Error fetching appointments:", error);
            appointmentListUl.innerHTML = "<li><span class='error'>Erro ao carregar agendamentos.</span></li>";
             displayMessage(appointmentAdminResultDiv, "Erro ao carregar agendamentos.", false);
        }
    };

    // --- Rendering Functions ---
    const renderServices = (services) => {
        serviceSelect.innerHTML = "<option value=''>-- Selecione um Serviço --</option>"; // Placeholder
        services.forEach(service => {
            const option = document.createElement("option");
            option.value = service.id;
            option.textContent = `${service.name} (${service.duration} min) - R$ ${service.price.toFixed(2)}`;
            option.dataset.duration = service.duration; // Store duration
            serviceSelect.appendChild(option);
        });
    };

    const renderAvailableSlots = (slots) => {
        slotsContainer.innerHTML = ""; // Clear previous slots
        if (slots.length === 0) {
            slotsContainer.innerHTML = "<p>Nenhum horário disponível para esta data e serviço.</p>";
            return;
        }
        slots.forEach(slotISO => {
            const slotButton = document.createElement("button");
            slotButton.className = "slot-button";
            slotButton.textContent = formatDate(slotISO).split(' ')[1]; // Show only HH:MM
            slotButton.dataset.datetime = slotISO; // Store full ISO time
            slotButton.addEventListener("click", () => handleSlotSelection(slotISO));
            slotsContainer.appendChild(slotButton);
        });
    };
    
    const renderAdminServices = (services) => {
        serviceListUl.innerHTML = ""; // Clear list
        if (services.length === 0) {
             serviceListUl.innerHTML = "<li>Nenhum serviço cadastrado.</li>";
             return;
        }
        services.forEach(service => {
            const li = document.createElement("li");
            li.innerHTML = `
                <span><b>${service.name}</b> (${service.duration} min) - R$ ${service.price.toFixed(2)}</span>
                <span class="admin-actions">
                    <button class="edit-service-btn" data-id="${service.id}">Editar</button>
                    <button class="delete-service-btn" data-id="${service.id}">Excluir</button>
                </span>
            `;
            serviceListUl.appendChild(li);
        });
        // Add event listeners after rendering
        document.querySelectorAll(".edit-service-btn").forEach(btn => btn.addEventListener("click", handleEditService));
        document.querySelectorAll(".delete-service-btn").forEach(btn => btn.addEventListener("click", handleDeleteService));
    };
    
     const renderAppointments = (appointments) => {
        appointmentListUl.innerHTML = ""; // Clear list
        if (appointments.length === 0) {
             appointmentListUl.innerHTML = "<li>Nenhum agendamento encontrado.</li>";
             return;
        }
        appointments.forEach(app => {
            const li = document.createElement("li");
            li.innerHTML = `
                <span>${formatDate(app.appointment_time)}</span>
                <span><b>${app.client_name}</b> (${app.client_phone})</span>
                <span><i>${app.service_name}</i></span>
                <!-- Add delete/cancel button if needed -->
            `;
            appointmentListUl.appendChild(li);
        });
    };

    // --- Event Handlers ---
    const handleSlotSelection = (dateTimeISO) => {
        const selectedServiceOption = serviceSelect.options[serviceSelect.selectedIndex];
        confirmService.textContent = selectedServiceOption.textContent.split(' - ')[0]; // Get only name and duration
        confirmDatetime.textContent = formatDate(dateTimeISO);
        bookingForm.dataset.datetime = dateTimeISO; // Store selected datetime on the form
        bookingForm.style.display = "block";
        bookingResultDiv.style.display = "none"; // Hide previous results
        clientNameInput.focus();
    };

    const handleBookingFormSubmit = (event) => {
        event.preventDefault();
        const bookingData = {
            client_name: clientNameInput.value.trim(),
            client_phone: clientPhoneInput.value.trim(),
            service_id: serviceSelect.value,
            appointment_time: bookingForm.dataset.datetime, // Get stored datetime
        };
        if (!bookingData.client_name || !bookingData.client_phone || !bookingData.service_id || !bookingData.appointment_time) {
            displayMessage(bookingResultDiv, "Por favor, preencha todos os campos e selecione um horário.", false);
            return;
        }
        submitBooking(bookingData);
    };

    const handleServiceFormSubmit = (event) => {
        event.preventDefault();
        const serviceData = {
            name: serviceNameInput.value.trim(),
            duration: parseInt(serviceDurationInput.value, 10),
            price: parseFloat(servicePriceInput.value),
        };
        
        if (!serviceData.name || isNaN(serviceData.duration) || serviceData.duration <= 0 || isNaN(serviceData.price) || serviceData.price < 0) {
             displayMessage(serviceAdminResultDiv, "Por favor, preencha todos os campos do serviço corretamente.", false);
             return;
        }

        const serviceId = serviceIdInput.value;
        let method = "POST";
        let url = `${ADMIN_API_BASE_URL}/services`;

        if (serviceId) { // If ID exists, it's an update
            method = "PUT";
            url = `${ADMIN_API_BASE_URL}/services/${serviceId}`;
        }
        
        saveService(serviceData, method, url);
    };
    
    const clearServiceForm = () => {
        serviceForm.reset();
        serviceIdInput.value = ""; // Ensure hidden ID is cleared
        saveServiceBtn.textContent = "Salvar Serviço";
    };
    
    const handleEditService = async (event) => {
        const serviceId = event.target.dataset.id;
        // Fetch the specific service data to populate the form
         try {
            const response = await fetch(`${ADMIN_API_BASE_URL}/services/${serviceId}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const service = await response.json();
            
            serviceIdInput.value = service.id;
            serviceNameInput.value = service.name;
            serviceDurationInput.value = service.duration;
            servicePriceInput.value = service.price;
            saveServiceBtn.textContent = "Atualizar Serviço";
            serviceNameInput.focus(); // Focus on the first field
            
        } catch (error) {
            console.error("Error fetching service for edit:", error);
            displayMessage(serviceAdminResultDiv, "Erro ao carregar dados do serviço para edição.", false);
        }
    };
    
    const handleDeleteService = (event) => {
        const serviceId = event.target.dataset.id;
        deleteService(serviceId);
    };

    // --- Initialization ---
    const initializeClientView = async () => {
        const services = await fetchServices(`${API_BASE_URL}/services`);
        renderServices(services);
        setMinDate();
        serviceSelect.addEventListener("change", () => {
            fetchAvailableSlots(serviceSelect.value, dateSelect.value);
        });
        dateSelect.addEventListener("change", () => {
            fetchAvailableSlots(serviceSelect.value, dateSelect.value);
        });
        bookingForm.addEventListener("submit", handleBookingFormSubmit);
        cancelBookingBtn.addEventListener("click", () => {
            bookingForm.style.display = "none";
            bookingForm.reset();
        });
    };
    
    const loadAdminServices = async () => {
        const services = await fetchServices(`${ADMIN_API_BASE_URL}/services`);
        renderAdminServices(services);
    };

    const initializeAdminView = () => {
        loadAdminServices();
        fetchAppointments(); // Load initial appointments
        serviceForm.addEventListener("submit", handleServiceFormSubmit);
        clearServiceFormBtn.addEventListener("click", clearServiceForm);
        refreshAppointmentsBtn.addEventListener("click", fetchAppointments);
    };

    // View Switching Logic
    showClientBtn.addEventListener("click", () => {
        adminView.style.display = "none";
        clientView.style.display = "block";
        initializeClientView(); // Re-initialize or refresh data if needed
    });

    showAdminBtn.addEventListener("click", () => {
        clientView.style.display = "none";
        adminView.style.display = "block";
        initializeAdminView(); // Load admin data when switching
    });

    // --- Start the application ---
    initializeClientView(); // Start with the client view
});

