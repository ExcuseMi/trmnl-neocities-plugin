function transform(input) {
  var html = typeof input.data === 'string' ? input.data : '';
  var items = [];

  var entities = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };
  function decode(s) { return s.replace(/&amp;|&lt;|&gt;|&quot;|&#39;/g, function(e) { return entities[e]; }); }

  var re = /<a\s+href="([^"]+)"\s+class="neo-Screen-Shot"\s+title="([^"]+)"[^>]*>[\s\S]*?<span[^>]+style="background:url\(([^)]+)\)/g;
  var match;

  while ((match = re.exec(html)) !== null) {
    var url   = match[1];
    var name  = decode(match[2]);
    var path  = match[3];
    var image = path.charAt(0) === '/' ? 'https://neocities.org' + path : path;
    items.push({ name: name, url: url, image: image });
  }

  // Shuffle so we don't always get the same 4 from the top of the page
  for (var i = items.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = items[i]; items[i] = items[j]; items[j] = tmp;
  }

  return { items: items.slice(0, 4) };
}
