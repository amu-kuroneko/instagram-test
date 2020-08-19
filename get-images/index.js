const requestPromiseNative = require('request-promise-native');
const fs = require('fs');
const mkdirp = require('mkdirp');

const words = [
  'love', // 1.83G
  'instagood', // 1.15G
  'photooftheday', // 790M
  'fashion', // 810M
  'beautiful', // 660M
  'happy', // 570M
  'cute', // 560M
  'tbt', // 530M
  'like4like', // 510M
  'followme', // 520M
];

const accessLogPath = 'logs/access';
const appLogPath = 'logs';

const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

const request = async (url) => {
  const result = await requestPromiseNative({ url, headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36' } });
  return result;
};

const formatDate = (date) => {
  const values = [
    [date.getFullYear(), 4],
    [date.getMonth() + 1, 2],
    [date.getDate(), 2],
    [date.getHours(), 2],
    [date.getMinutes(), 2],
    [date.getSeconds(), 2],
    [date.getMilliseconds(), 3],
  ].map(([value, digits]) => `${'0'.repeat(digits - `${value}`.length)}${value}`);
  return `${values.slice(0, 3).join('-')} ${values.slice(3, 6).join(':')}.${values[6]}`;
};

const accessLog = (message) => {
  const date = new Date();
  const formattedDate = formatDate(date);
  const directory = `${accessLogPath}/${formattedDate.replace(/(-| |:)/g, '/').replace(/\/[^/]+$/, '')}`;
  mkdirp.sync(directory);
  const filepath = `${directory}/${date.getSeconds()}-access.log`;
  fs.appendFileSync(filepath, `${date.getTime()}: ${message}\n`);
};

const appLog = (level, message) => {
  fs.appendFileSync(`${appLogPath}/instagram.log`, `[${level}] ${formatDate(new Date())}: ${message}\n`);
};

const errorLog = message => appLog('ERROR', message);
const infoLog = message => appLog('INFO ', message);
const debugLog = message => appLog('DEBUG', message);

const getFirstItems = async (tag) => {
  await sleep(2000);
  const url = `https://www.instagram.com/explore/tags/${encodeURIComponent(tag)}/?__a=1`;
  const result = await request(url);
  accessLog(JSON.stringify({ url, result }));
  try {
    return JSON.parse(result);
  } catch (error) {
    errorLog('Failed to parse json in getFirstItems');
    throw error;
  }
};

const getNextItems = async (tag, cursor) => {
  await sleep(2000);
  const variables = { tag_name: tag, first: 12, after: cursor };
  const url = `https://www.instagram.com/graphql/query/?query_hash=7dabc71d3e758b1ec19ffb85639e427b&variables=${encodeURIComponent(JSON.stringify(variables))}`;
  const result = await request(url);
  accessLog(JSON.stringify({ url, result }));
  try {
    return JSON.parse(result);
  } catch (error) {
    errorLog('Failed to parse json in getNextItems');
    throw error;
  }
};

const next = async (tag, cursor, count) => {
  const result = await getNextItems(tag, cursor);
  const { length } = result.data.hashtag.edge_hashtag_to_media.edges;
  debugLog(JSON.stringify({ count, length, total: count + length }));
  if (count + length < 1000 && result.data.hashtag.edge_hashtag_to_media.page_info.has_next_page) {
    await next(tag, result.data.hashtag.edge_hashtag_to_media.page_info.cursor, count + length);
  }
};

const requestToInstagram = async (tag) => {
  infoLog(`start to search with '${tag}'`);
  const result = await getFirstItems(tag);
  if (result.graphql.hashtag.edge_hashtag_to_media.page_info.has_next_page) {
    await next(
      tag,
      result.graphql.hashtag.edge_hashtag_to_media.page_info.cursor,
      result.graphql.hashtag.edge_hashtag_to_media.edges.length,
    );
  }
};

const start = async (i, numberOfTry = 0) => {
  try {
    await requestToInstagram(words[i % words.length]);
  } catch (error) {
    errorLog(error.toString());
    if (numberOfTry < 3) {
      infoLog('Try again to search');
      await start(i, numberOfTry + 1);
      return;
    }
    errorLog('Search next word because Over number of try.');
  }
  await start(i + 1);
};

const main = async () => {
  mkdirp.sync(accessLogPath);
  mkdirp.sync(appLogPath);
  await start(0);
};
main();
