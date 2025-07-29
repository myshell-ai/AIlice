function initFAQModal() {
    const faqButton = document.getElementById('faq-button');
    const faqModal = document.getElementById('faq-modal');
    const closeFaqModal = document.getElementById('close-faq-modal');
    const faqQuestions = document.querySelectorAll('.faq-question');

    // Open FAQ modal
    faqButton.addEventListener('click', function () {
        faqModal.style.display = 'block';
    });

    // Close FAQ modal
    closeFaqModal.addEventListener('click', function () {
        faqModal.style.display = 'none';
    });

    // FAQ accordion functionality
    faqQuestions.forEach(question => {
        question.addEventListener('click', function () {
            const answer = this.nextElementSibling;
            const isActive = this.classList.contains('active');

            // Close all other FAQ items
            faqQuestions.forEach(q => {
                q.classList.remove('active');
                q.nextElementSibling.classList.remove('active');
            });

            // Toggle current item
            if (!isActive) {
                this.classList.add('active');
                answer.classList.add('active');
            }
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', function (event) {
        if (event.target === faqModal) {
            faqModal.style.display = 'none';
        }
    });

    // Close modal with close button in header
    const closeButton = faqModal.querySelector('.close[data-modal-id="faq-modal"]');
    if (closeButton) {
        closeButton.addEventListener('click', function () {
            faqModal.style.display = 'none';
        });
    }
}