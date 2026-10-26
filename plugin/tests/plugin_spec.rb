# Run: trmnlp test (from plugin/)
SITES = [
  { name: 'Flamed Fury', url: 'https://flamedfury.neocities.org', image: 'https://neocities.org/site_screenshots/10/59/flamedfury/index.html.540x405.webp' },
  { name: 'caramelpuddinz', url: 'https://caramelpuddinz.neocities.org', image: 'https://neocities.org/site_screenshots/21/00/caramelpuddinz/index.html.540x405.webp' }
].freeze

RSpec.describe 'Neocities Sites' do
  %w[full half_horizontal half_vertical quadrant].each do |view|
    it "shows sites in #{view}" do
      screen = trmnl.render(view:, data: { items: SITES }, transform: false, custom_fields: { sort_by: 'random' })
      expect(screen).to have_no_overflow
      expect(screen).to have_no_problems
    end
  end

  # Transform and template together; neocities.org answers with a cut of its live page (3 sites)
  PAGE = File.read(File.join(__dir__, '..', 'test', 'browse-2026-10-25.html')).freeze

  it 'shows the sites the serverless transform reads from the browse page' do
    screen = trmnl.render(view: 'full', custom_fields: { sort_by: 'random' }, mocks: { 'https://neocities.org/browse*' => { body: PAGE } })
    sites = screen.evaluate('window.__nc || []')
    expect(sites.size).to eq(3)
    expect(sites).to all(include('url' => start_with('https://'), 'image' => include('/site_screenshots/')))
    expect(screen).to have_no_problems
  end

  it 'says Neocities is unreachable when it is down and there is nothing to show yet' do
    screen = trmnl.render(view: 'full', custom_fields: { sort_by: 'random' }, mocks: { 'https://neocities.org/browse*' => { status: 503 } })
    expect(screen).to have_text('Neocities is unreachable')
    expect(screen).to have_no_problems
  end
end
