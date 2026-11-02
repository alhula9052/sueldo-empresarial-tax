document.addEventListener('DOMContentLoaded', () => {
 const toggle = document.querySelector('.menu-toggle');
 if (toggle) toggle.addEventListener('click', () => {
  const expanded = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(expanded));
  document.body.classList.toggle('menu-open', expanded);
 });
 document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', e => {
  if (!window.confirm(form.dataset.confirm)) e.preventDefault();
 }));
});
