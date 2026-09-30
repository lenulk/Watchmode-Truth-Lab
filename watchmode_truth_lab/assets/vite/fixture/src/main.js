import { token } from './token.js';

import { renderToken, initCounter } from './view.js';
initCounter();
renderToken(token);

if (import.meta.hot) {
  import.meta.hot.accept('./token.js', (updated) => {
    renderToken(updated.token);
  });
}
