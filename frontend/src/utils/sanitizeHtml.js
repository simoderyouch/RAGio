import DOMPurify from 'dompurify';

export function sanitizeHtml(htmlString) {
	if (typeof htmlString !== 'string') return '';
	try {
		return DOMPurify.sanitize(htmlString, { USE_PROFILES: { html: true } });
	} catch (_) {
		return '';
	}
}

export default sanitizeHtml;

