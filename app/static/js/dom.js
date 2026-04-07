export function el(id) {
  return document.getElementById(id);
}

export function setText(id, value) {
  el(id).textContent = value;
}

export function setStatus(id, value, type = "success") {
  const node = el(id);
  node.textContent = value || "";
  node.classList.remove("error");
  if (type === "error" && value) {
    node.classList.add("error");
  }
}
