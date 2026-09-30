import { token } from './token.js';

window.__wtl_session = crypto.randomUUID();
window.__wtl_updates = 0;
document.querySelector('#token').textContent = token;

if (import.meta.hot) {
  import.meta.hot.accept('./token.js', (updated) => {
    document.querySelector('#token').textContent = updated.token;
    window.__wtl_updates += 1;
  });
}
