/**
 * Studio Vidéo — VideoAsk → Google Drive
 *
 * Reçoit le webhook VideoAsk (événement form_response) et enregistre chaque
 * réponse vidéo dans le dossier RUSHES du Drive.
 * Gratuit (Google Apps Script), fichiers jusqu'à 50 Mo.
 *
 * Installation :
 *  1. Coller ce code dans un projet Apps Script (script.google.com).
 *  2. Mettre l'ID du dossier RUSHES dans FOLDER_ID et une clé dans SECRET.
 *  3. Déployer > Nouveau déploiement > Application Web
 *     (Exécuter en tant que : moi ; Accès : Tout le monde). Autoriser.
 *  4. Copier l'URL /exec, ajouter ?k=SECRET et la coller dans VideoAsk :
 *     videoask > Connect > Webhooks > événement « form_response ».
 */

const FOLDER_ID = '{{FOLDER_ID}}'; // STUDIO VIDÉO/BIBLIOTHÈQUE/RUSHES (rempli par le skill)
const SECRET = '{{SECRET}}'; // clé aléatoire (remplie par le skill)
const TZ = 'Africa/Lagos';

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    if (SECRET && (!e.parameter || e.parameter.k !== SECRET)) return out_('forbidden');
    const body = JSON.parse(e.postData.contents);
    const type = body.event_type || '';
    if (type && type !== 'form_response' && type !== 'form_response_transcribed') return out_('ignored ' + type);
    return out_('ok ' + saveResponse_(body));
  } catch (err) {
    console.error(err);
    return out_('error ' + err);
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return out_('Studio Vidéo — VideoAsk → Drive : actif');
}

/** Enregistre les vidéos d'une réponse. Renvoie le nombre de fichiers créés. */
function saveResponse_(body) {
  const contact = body.contact || {};
  const answers = contact.answers || [];
  const form = body.form || {};
  const folder = DriveApp.getFolderById(FOLDER_ID);
  const who = clean_(contact.name || 'Anonyme');
  const when = Utilities.formatDate(new Date(contact.created_at || Date.now()), TZ, 'yyyy-MM-dd_HHmm');
  const order = {};
  (form.questions || []).forEach(function (q, i) { order[q.question_id] = i + 1; });

  let created = 0;
  answers.forEach(function (a, i) {
    if (!a.media_url) return;
    if (a.type && a.type !== 'video') return;
    const n = order[a.question_id] || (i + 1);
    const name = who + '_' + when + '_Q' + ('0' + n).slice(-2) + '.mp4';
    if (folder.getFilesByName(name).hasNext()) return; // déjà reçu
    const blob = UrlFetchApp.fetch(a.media_url).getBlob().setName(name);
    const file = folder.createFile(blob);
    file.setDescription(JSON.stringify({
      source: 'videoask',
      form: form.title || form.form_id || '',
      contact: contact.name || '',
      contact_id: contact.contact_id || '',
      question_id: a.question_id || '',
      transcription: a.transcription || '',
      share_url: a.share_url || ''
    }));
    created++;
  });
  return created;
}

function clean_(s) {
  return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40) || 'Anonyme';
}

function out_(msg) {
  return ContentService.createTextOutput(msg);
}

/** Test manuel depuis l'éditeur : vérifie l'accès au dossier. */
function testFolder() {
  console.log(DriveApp.getFolderById(FOLDER_ID).getName());
}
