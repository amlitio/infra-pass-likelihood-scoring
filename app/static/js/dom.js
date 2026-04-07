export function el(id) {
  return document.getElementById(id);
}

export function setText(id, value) {
  el(id).textContent = value;
}
