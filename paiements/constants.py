PAYMENT_PROVIDERS = [
    {
        'id': 'sandbox',
        'nom': '🧪 Paiement test (sandbox)',
        'description': 'Mode test — aucun argent réel',
        'icone': '🧪',
        'disponible': True,
    },
    {
        'id': 'fedapay',
        'nom': 'FedaPay',
        'description': 'Mobile Money, carte bancaire (Togo/Bénin)',
        'icone': '📱',
        'disponible': False,
    },
    {
        'id': 'cinetpay',
        'nom': 'CinetPay',
        'description': 'Mobile Money, carte Visa (Afrique de l\'Ouest)',
        'icone': '💳',
        'disponible': False,
    },
    {
        'id': 'mixx',
        'nom': 'Mixx by YAS',
        'description': 'Wave, Flooz, T-Money (Togo)',
        'icone': '📲',
        'disponible': False,
    },
    {
        'id': 'stripe',
        'nom': 'Stripe',
        'description': 'Carte bancaire internationale (Visa, Mastercard)',
        'icone': '🌍',
        'disponible': False,
    },
]
