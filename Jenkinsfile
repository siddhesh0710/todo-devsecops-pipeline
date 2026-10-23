pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .venv-ci
                    . .venv-ci/bin/activate
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . .venv-ci/bin/activate
                    pytest -v --junitxml=test-results.xml
                '''
            }
        }
    }

    post {
        always {
            junit testResults: 'test-results.xml',
                  allowEmptyResults: true
        }
        success {
            echo 'All tests passed!'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs.'
        }
    }
}
