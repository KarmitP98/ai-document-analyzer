export const environment = {
  production: true,
  blobStorage: {
    accountName: '#{blob-storage-account-name}#',
    folders: {
      pdfs: 'pdfs',
      labels: 'labelled',
      entities: 'entities',
      vocabularies: 'vocabs',
      features: 'features',
      locations: 'locations'
    },
    containers: {
      data: '#{container-name}#'
    }
  },
  tableStorage: {
    accountName: '#{table-storage-account-name}#',
    names:
      {
        programs: 'Programs',
        clients: 'Clients',
        users: 'Users',
        vocabularies: 'Vocabularies',
        netXFolders: 'NetXFolders'
      }
  },
  queueStorage: {
    accountName: '#{blob-storage-account-name}#',
    names: {
      smartCapture: 'smart-capture',
    }
  },
  functions: {
    appName: '#{function-app-name}#',
    names: {
      tableStorageToken: 'generate-table-storage-token',
      blobStorageToken: 'generate-blob-storage-token',
      netXUpload: 'netx-upload',
      vocabMatching: 'vocab-matching',
      clientVerification: 'new-client-verification',
      poi: 'bing_maps',
      netXLogin: 'netx-login',
      vocabUpload: 'vocab-upload',
      pageLabelling: 'page-labelling',
      downloadProgramAssets: 'download-program-data',
      labelPrograms: 'label-programs',
    },
    key: {
      name: 'default',
      value: '#{function-key}#'
    }
  },
  bing: {
    key: '#{bing-key}#'
  },
  azure: {
    key: '#{azure-maps-key}#'
  },
  config: {
    auth: {
      clientId: '#{azure-config-auth-clientId}#'
    },
    b2cPolicies: {
      names: {
        signIn: '#{azure-config-b2cPolicies-names-signIn}#'
      },
      authorities: {
        signIn: {
          authority: '#{azure-config-b2cPolicies-authorities-signIn-authority}#'
        }
      },
      authorityDomain: '#{azure-config-b2cPolicies-authorityDomain}#'
    }

  }
};
