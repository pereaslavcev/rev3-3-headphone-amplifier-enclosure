const image = document.querySelector('#main-image');
const buttons = [...document.querySelectorAll('.thumb')];
for (const button of buttons) {
  button.addEventListener('click', () => {
    image.src = button.dataset.src;
    image.alt = button.dataset.alt;
    for (const item of buttons) item.classList.toggle('active', item === button);
  });
}
window.__SCENE_READY__ = true;
window.__seek = () => {};
