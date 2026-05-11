function transform(input) {
  var raw = Array.isArray(input.data) ? input.data : [];
  return { items: raw };
}
