import { CRISIS_KEYWORDS, CVV_MESSAGE } from './constants';

export function detectCrisisKeywords(text: string): boolean {
  const lowerText = text.toLowerCase();
  return CRISIS_KEYWORDS.some(keyword => lowerText.includes(keyword));
}

export function getCrisisMessage(): string {
  return CVV_MESSAGE;
}

export function getCrisisModalContent() {
  return {
    title: 'Estamos aqui por você',
    message: `Percebemos que você pode estar passando por um momento muito difícil. 
    
${CVV_MESSAGE}

Você também pode buscar ajuda profissional imediata:
• SAMU: 192
• Bombeiros: 193
• Emergências: 188 (CVV)

Lembre-se: você não está sozinha. Há pessoas que se importam e querem te ajudar.`,
    actions: [
      {
        label: 'Ligar para o CVV (188)',
        href: 'tel:188',
        primary: true,
      },
      {
        label: 'Encontrar um psicólogo',
        href: '/therapists',
        primary: false,
      },
    ],
  };
}