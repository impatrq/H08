/* ══════════════════════════════════════
   PROYECTO H-08 — main.js
   E.T. N°7 IMPA · Quilmes · Buenos Aires
   ══════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ─── NAVBAR: shrink on scroll ─── */
  const navbar = document.getElementById('navbar');

  window.addEventListener('scroll', () => {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }, { passive: true });


  /* ─── NAVBAR: mobile toggle ─── */
  const navToggle = document.getElementById('navToggle');
  const navMenu   = document.getElementById('navMenu');

  navToggle.addEventListener('click', () => {
    navToggle.classList.toggle('open');
    navMenu.classList.toggle('open');
  });

  // Cerrar menú al hacer click en un link
  navMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navToggle.classList.remove('open');
      navMenu.classList.remove('open');
    });
  });


  /* ─── SMOOTH SCROLL para links internos ─── */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const navH = navbar.offsetHeight;
      const top  = target.getBoundingClientRect().top + window.scrollY - navH;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });


  /* ─── SCROLL ANIMATIONS (IntersectionObserver) ─── */
  const animElements = document.querySelectorAll('[data-animate]');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;

      const el    = entry.target;
      const delay = parseInt(el.dataset.delay || '0', 10);

      setTimeout(() => {
        el.classList.add('visible');
      }, delay);

      observer.unobserve(el);
    });
  }, {
    threshold: 0.12,
    rootMargin: '0px 0px -40px 0px'
  });

  animElements.forEach(el => observer.observe(el));


  /* ─── ACTIVE NAV LINK on scroll ─── */
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('#navMenu a');

  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        navLinks.forEach(link => {
          link.style.color = '';
        });
        const activeLink = document.querySelector(`#navMenu a[href="#${entry.target.id}"]`);
        if (activeLink) activeLink.style.color = 'var(--cream)';
      }
    });
  }, {
    threshold: 0.45
  });

  sections.forEach(s => sectionObserver.observe(s));


  /* ─── SPEC PANEL: hover highlight ─── */
  document.querySelectorAll('.spec-row').forEach(row => {
    row.addEventListener('mouseenter', () => {
      row.style.background = 'rgba(184, 92, 42, 0.06)';
      row.style.paddingLeft = '6px';
      row.style.transition = 'all 0.2s ease';
    });
    row.addEventListener('mouseleave', () => {
      row.style.background = '';
      row.style.paddingLeft = '';
    });
  });


  /* ─── FASE CARDS: stagger on load ─── */
  document.querySelectorAll('.fase-card').forEach((card, i) => {
    card.style.transitionDelay = `${i * 80}ms`;
  });


  /* ─── YEAR en footer (mantiene actualizado) ─── */
  const yearEl = document.querySelector('footer p');
  if (yearEl) {
    const year = new Date().getFullYear();
    yearEl.textContent = yearEl.textContent.replace(/\d{4}/, year);
  }

});
