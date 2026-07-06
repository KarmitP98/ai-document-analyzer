export const appRoutes =
  {
    clients: {name: 'clients', path: 'clients', pathArray: ['/', 'clients']},
    login: {name: 'login', path: 'login', pathArray: ['/', 'login']},
    home: {name: 'home', path: 'home', pathArray: ['/', 'home']},
    pageLabelling: {name: '', path: 'page-labelling', pathArray: ['/', 'page-labelling']},
    programAnalysis: {name: 'program-analysis', path: 'program-analysis', pathArray: ['/', 'program-analysis']},
    programReview: {name: 'program-review', path: 'program-review', pathArray: ['/', 'program-review']},
    admin: {
      name: 'admin', path: 'admin', pathArray: ['/', 'admin'],
      children: {
        users: {name: 'users', path: 'users', pathArray: ['/', 'admin', 'users']},
        vocab: {name: 'vocab', path: 'vocab', pathArray: ['/', 'admin', 'vocab']}
      }
    },
    sandbox: {name: 'sandbox', path: 'sandbox101', pathArray: ['/', 'sandbox101']},
  };
