"""Configuration for document formatting."""

DOCUMENT_FORMATTING = {
    # Heading settings for different levels
    'headings': {
        1: {
            'font_size': 16,
            'font_color': (0, 0, 0),  # Black
            'space_before': 12,
            'space_after': 6
        },
        2: {
            'font_size': 14,
            'font_color': (0, 0, 0),  # Black
            'space_before': 10,
            'space_after': 6
        },
        3: {
            'font_size': 12,
            'font_color': (0, 0, 0),  # Black
            'space_before': 8,
            'space_after': 6
        }
    },
    
    # Default text settings
    'default_text': {
        'font_size': 11,
        'font_color': (0, 0, 0),  # Black
        'space_before': 6,
        'space_after': 6,
        'line_spacing': 1.15
    }
}
