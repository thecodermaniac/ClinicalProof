module.exports = {
  generateRandomPmid: (context, events, done) => {
    const pmids = ['12345678', '87654321', '11223344', '55667788'];
    context.vars.pmid = pmids[Math.floor(Math.random() * pmids.length)];
    done();
  }
};