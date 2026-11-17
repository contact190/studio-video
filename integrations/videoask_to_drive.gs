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

function doGet(e) {
  const prm = (e && e.parameter) || {};
  if (prm.action === 'fetch') {
    if (SECRET && prm.k !== SECRET) return out_('forbidden');
    return fetchToDrive_(prm);
  }
  return out_('Studio Vidéo — VideoAsk → Drive : actif');
}

/**
 * Télécharge une vidéo (pub Meta) directement dans STUDIO VIDÉO/BIBLIOTHÈQUE/RÉFÉRENCES/<sub>.
 * ?action=fetch&k=<clé>&url=<lien vidéo>&name=<nom.mp4>&sub=META
 * Réponse JSON : {ok, id, name, size, existing}. Limite Google : 50 Mo par fichier.
 */
function fetchToDrive_(prm) {
  try {
    const url = String(prm.url || '');
    if (!/^https:\/\/[^/]*(fbcdn\.net|facebook\.com|fbsbx\.com|cdninstagram\.com)\//.test(url)) {
      return json_({ok: false, error: 'lien non autorisé (Meta uniquement)'});
    }
    const name = String(prm.name || 'meta.mp4').replace(/[\\/:*?"<>|]/g, '_');
    const lib = DriveApp.getFolderById(FOLDER_ID).getParents().next();       // BIBLIOTHÈQUE
    const refs = child_(lib, 'RÉFÉRENCES');
    const dest = child_(refs, String(prm.sub || 'META'));
    const same = dest.getFilesByName(name);
    if (same.hasNext()) {
      const f = same.next();
      return json_({ok: true, id: f.getId(), name: name, size: f.getSize(), existing: true});
    }
    const r = UrlFetchApp.fetch(url, {followRedirects: true, muteHttpExceptions: true});
    if (r.getResponseCode() !== 200) return json_({ok: false, error: 'HTTP ' + r.getResponseCode()});
    const f = dest.createFile(r.getBlob().setName(name));
    return json_({ok: true, id: f.getId(), name: name, size: f.getSize(), existing: false});
  } catch (err) {
    return json_({ok: false, error: String(err)});
  }
}

function child_(parent, name) {
  const it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
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
